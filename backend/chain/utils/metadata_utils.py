from typing import Dict, List, Tuple
import re
import unicodedata

def _norm_section_token(raw: str) -> str:
        """Normalize '153-b'/'153B'/'376AB'/'41' -> '153B','376AB','41' (no hyphens, suffix upper)."""
        tok = re.sub(r"[\s\-]+", "", raw or "")
        m = re.match(r"^(\d{1,4})([A-Za-z]{0,3})$", tok)
        if not m:
            return tok.upper()
        num, suf = m.groups()
        return num + (suf.upper() if suf else "")

def _norm_token(s: str) -> str:
        s = str(s or "")
        s = s.strip()
        s = s.replace(" ", "_")
        s = re.sub(r"[^a-zA-Z0-9_\-]", "", s)
        return s.lower()

def extract_legal_metadata(text: str, filename: str) -> Dict:
    """
    Extract legal metadata with improved section detection and better filtering.
    """

    # ----------------- helpers -----------------

    def _is_valid_section_token(sec: str) -> bool:
        """
        Improved validation for section tokens:
        - Accept sections like 120A, 120B, 376AB
        - Accept multi-digit sections like 196, 197, 153B
        - Reject single digits (1-9) and obvious page numbers
        - Accept sections with letter suffixes even if single digit (9A, but not plain 9)
        """
        sec = sec.strip()
        
        # Reject obvious non-sections
        if not sec or len(sec) > 6:
            return False
            
        # Multi-digit sections (10+) with optional letters are always valid
        if re.fullmatch(r"\d{2,4}[A-Za-z]{0,3}", sec):
            return True
            
        # Single digit with required letter suffix (9A, 9B, etc.)
        if re.fullmatch(r"\d[A-Za-z]{1,3}", sec):
            return True
            
        return False

    def _infer_primary_act(filename: str, head_text: str) -> Tuple[str, str]:
        f = (filename or "").lower()
        t = (head_text or "")
        
        if "repealedfileopen" in f or "indian_penal_code" in f or "ipc" in f:
            return ("indian_penal_code", "Indian Penal Code, 1860")
        if "code_of_criminal_procedure" in f or "crpc" in f:
            return ("code_of_criminal_procedure", "Code of Criminal Procedure, 1973")
        if "constitution" in f:
            return ("constitution_of_india", "Constitution of India")
            
        # Check content for act identification
        if re.search(r"\bTHE\s+INDIAN\s+PENAL\s+CODE\b", t, re.IGNORECASE):
            return ("indian_penal_code", "Indian Penal Code, 1860")
        if re.search(r"\bTHE\s+CODE\s+OF\s+CRIMINAL\s+PROCEDURE\b", t, re.IGNORECASE):
            return ("code_of_criminal_procedure", "Code of Criminal Procedure, 1973")
        if re.search(r"\bTHE\s+CONSTITUTION\s+OF\s+INDIA\b", t, re.IGNORECASE):
            return ("constitution_of_india", "Constitution of India")
            
        return ("unknown_act", "Unknown")

    def _looks_like_page_or_counter(line: str) -> bool:
        """Detect page numbers and other counter-like content"""
        line = line.strip()
        
        # Pure numbers (especially small ones) on their own line
        if re.fullmatch(r"\d{1,3}", line):
            return True
            
        # Roman numerals
        if re.fullmatch(r"[ivxlcdm]{1,6}[.)]?", line, flags=re.IGNORECASE):
            return True
            
        # Page indicators
        if re.fullmatch(r"(?:page\s*)?\d{1,4}(?:\s*of\s*\d{1,4})?", line, flags=re.IGNORECASE):
            return True
            
        return False

    def _looks_like_ipc_offence_table(block: str) -> bool:
        """Detect CrPC tables that list IPC offences"""
        t = block.lower()
        return ("cognizable" in t and "bailable" in t) and ("court of" in t or "punishment" in t)

    # ---------- normalize text ----------
    text = unicodedata.normalize("NFKC", text)
    lines = text.splitlines()

    metadata: Dict = {
        "source_file": filename,
        "document_type": "legal_document",
        "jurisdiction": "india",
        "extracted_acts": [],
        "extracted_acts_norm": [],
        "extracted_sections": [],
        "extracted_sections_norm": [],
        "referenced_sections": [],
        "referenced_acts": [],
        "legal_topics": [],
        "legal_topics_norm": [],
        "complexity_level": "intermediate",
        "filename_norm": _norm_token(filename),
    }

    # ---------- primary act ----------
    head_text = "\n".join(lines[:100])
    primary_act_key, primary_act_display = _infer_primary_act(filename, head_text)
    if primary_act_key != "unknown_act":
        metadata["extracted_acts"] = [primary_act_display]
        metadata["extracted_acts_norm"] = [_norm_token(primary_act_display)]

    # ---------- Extract additional acts (Act X of YYYY format) ----------
    act_references = []
    act_patterns = [
        r'\bAct\s+(\d+)\s+of\s+(\d{4})\b',  # "Act 8 of 1913"
        r'\b(\d+)\s+of\s+(\d{4})\b',        # "45 of 1860" (Indian Penal Code reference)
    ]
    
    for pattern in act_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            act_num = match.group(1)
            year = match.group(2)
            act_ref = f"Act {act_num} of {year}"
            if act_ref not in act_references:
                act_references.append(act_ref)
    
    # Add to metadata if found
    if act_references:
        if metadata["extracted_acts"]:
            metadata["extracted_acts"].extend(act_references)
        else:
            metadata["extracted_acts"] = act_references
        
        if metadata["extracted_acts_norm"]:
            metadata["extracted_acts_norm"].extend([_norm_token(act) for act in act_references])
        else:
            metadata["extracted_acts_norm"] = [_norm_token(act) for act in act_references]

    # ---------- Improved section extraction ----------
    contained_sections: List[str] = []
    seen_contained = set()

    # More flexible patterns
    SECTION_WITH_EMDASH_RE = re.compile(
        r'\b(\d{1,4}[A-Za-z]{0,3})\.\s+[A-Z][^—\n]*\s*—',  # Handle space before em-dash
        re.IGNORECASE
    )

    SECTION_WITH_TITLE_RE = re.compile(
        r'\b(\d{1,4}[A-Za-z]{0,3})\.\s+[A-Z][^\n.]{8,}',  # Section with title, more flexible
        re.IGNORECASE
    )

    # Method 1: Find sections with em-dash (more flexible)
    for match in SECTION_WITH_EMDASH_RE.finditer(text):
        raw = match.group(1)
        sec = _norm_section_token(raw)
        
        if _is_valid_section_token(sec) and sec not in seen_contained:
            seen_contained.add(sec)
            contained_sections.append(sec)
    # Method 2: Find sections with titles
    for match in SECTION_WITH_TITLE_RE.finditer(text):
        raw = match.group(1)
        sec = _norm_section_token(raw)
        
        if _is_valid_section_token(sec) and sec not in seen_contained:
            seen_contained.add(sec)
            contained_sections.append(sec)

    # Method 3: Process lines more aggressively
    in_sections_list = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip obvious page numbers and very short lines
        if _looks_like_page_or_counter(line_stripped) or len(line_stripped) < 3:
            continue
            
        # More flexible SECTIONS detection
        if re.search(r'\bSECTIONS?\b', line_stripped, flags=re.IGNORECASE):
            in_sections_list = True
            continue
            
        if in_sections_list:
            # Exit SECTIONS mode
            if (re.match(r'^CHAPTER\b', line_stripped, flags=re.IGNORECASE) or 
                re.match(r'^[A-Z][A-Z ]{8,}$', line_stripped)):
                in_sections_list = False
                continue
                
            # In SECTIONS mode, be more aggressive
            # Look for any number followed by optional letters, then a period
            section_matches = re.findall(r'\b(\d{1,4}[A-Za-z]{0,3})\.\s', line_stripped)
            for raw in section_matches:
                sec = _norm_section_token(raw)
                if (_is_valid_section_token(sec) and 
                    sec not in seen_contained):
                    seen_contained.add(sec)
                    contained_sections.append(sec)
        else:
            # Outside SECTIONS mode, look for section patterns
            # More flexible pattern matching
            section_match = re.match(r'^(\d{1,4}[A-Za-z]{0,3})\.\s+[A-Z]', line_stripped)
            if section_match:
                raw = section_match.group(1)
                sec = _norm_section_token(raw)
                
                if _is_valid_section_token(sec) and sec not in seen_contained:
                    # Additional context check for CrPC IPC tables
                    start = max(0, i - 2)
                    end = min(len(lines), i + 6)
                    block = "\n".join(lines[start:end])
                    
                    # Skip if this is in an IPC offence table within CrPC
                    if (primary_act_key == "code_of_criminal_procedure" and 
                        _looks_like_ipc_offence_table(block)):
                        continue
                        
                    seen_contained.add(sec)
                    contained_sections.append(sec)

    # Also capture inline "section X" occurrences that may appear in running text
    # (e.g. "section 117 or sub-section (2) of section 138") and add them if valid.
    INLINE_SECTION_RE = re.compile(r'\bsection[s]?\s*\.?\s*\(?\s*([0-9]{1,4}[A-Za-z]{0,3})\b', re.IGNORECASE)
    for m in INLINE_SECTION_RE.finditer(text):
        raw = m.group(1)
        sec = _norm_section_token(raw)
        if _is_valid_section_token(sec) and sec not in seen_contained:
            seen_contained.add(sec)
            contained_sections.append(sec)

    metadata["extracted_sections"] = contained_sections
    # Use section normalizer to produce canonical lowercase tokens for matching
    metadata["extracted_sections_norm"] = [_norm_section_token(s).lower() for s in contained_sections]

    # ---------- Cross-act references ----------
    ref_patterns = [
        (r'\bsections?\s+([0-9]{1,4}[A-Za-z]{0,3}(?:\s*(?:,|and)\s*[0-9]{1,4}[A-Za-z]{0,3})*)\s+of\s+the\s+Indian\s+Penal\s+Code', 'indian_penal_code'),
        (r'\bsections?\s+([0-9]{1,4}[A-Za-z]{0,3}(?:\s*(?:,|and)\s*[0-9]{1,4}[A-Za-z]{0,3})*)\s+(?:IPC|I\.P\.C\.)\b', 'indian_penal_code'),
        (r'\bsections?\s+([0-9]{1,4}[A-Za-z]{0,3}(?:\s*(?:,|and)\s*[0-9]{1,4}[A-Za-z]{0,3})*)\s+of\s+the\s+Code\s+of\s+Criminal\s+Procedure', 'code_of_criminal_procedure'),
        (r'\bsections?\s+([0-9]{1,4}[A-Za-z]{0,3}(?:\s*(?:,|and)\s*[0-9]{1,4}[A-Za-z]{0,3})*)\s+(?:CrPC|C\.r\.P\.C\.|Cr\.P\.C\.)\b', 'code_of_criminal_procedure'),
        (r'\bu/s\.?\s*([0-9]{1,4}[A-Za-z]{0,3})\s+(?:IPC|I\.P\.C\.)\b', 'indian_penal_code'),
        (r'\bu/s\.?\s*([0-9]{1,4}[A-Za-z]{0,3})\s+(?:CrPC|C\.r\.P\.C\.|Cr\.P\.C\.)\b', 'code_of_criminal_procedure'),
        (r'\bsection\s+([0-9]{1,4}[A-Za-z]{0,3}).{0,40}\b(?:IPC|Indian\s+Penal\s+Code)\b', 'indian_penal_code'),
        (r'\bsection\s+([0-9]{1,4}[A-Za-z]{0,3}).{0,40}\b(?:CrPC|Code\s+of\s+Criminal\s+Procedure)\b', 'code_of_criminal_procedure'),
    ]

    referenced_sections = []
    referenced_acts = set()

    def _split_multi_sections(group: str) -> List[str]:
        parts = re.split(r'\s*(?:,|and)\s*', group.strip())
        out = []
        for p in parts:
            if p:
                out.append(_norm_section_token(p))
        return out

    for pat, canon in ref_patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE | re.DOTALL):
            g = m.group(1)
            secs = _split_multi_sections(g)
            for s in secs:
                if _is_valid_section_token(s):
                    referenced_sections.append({"section": s, "act": canon})
                    referenced_acts.add(canon)

    # Remove duplicates from referenced_sections
    seen_refs = set()
    unique_refs = []
    for ref in referenced_sections:
        ref_key = (ref["section"], ref["act"])
        if ref_key not in seen_refs:
            seen_refs.add(ref_key)
            unique_refs.append(ref)
    
    # Remove primary act from referenced acts
    if primary_act_key in referenced_acts:
        referenced_acts.remove(primary_act_key)

    metadata["referenced_sections"] = unique_refs
    metadata["referenced_acts"] = sorted(referenced_acts)

    # ---------- Legal topics ----------
    tl = text.lower()
    topics = []
    if any(k in tl for k in ["criminal", "police", "fir", "conspiracy", "murder", "theft"]):
        topics.append("criminal")
    if any(k in tl for k in ["contract", "property", "damages", "civil", "suit"]):
        topics.append("civil")
    if any(k in tl for k in ["fundamental rights", "directive principles", "constitution"]):
        topics.append("constitutional")
    if any(k in tl for k in ["marriage", "divorce", "custody", "maintenance"]):
        topics.append("family")
        
    metadata["legal_topics"] = topics
    metadata["legal_topics_norm"] = [_norm_token(t) for t in topics]
    
    return metadata

def identify_document_type(filename:str, text:str) -> str:
        """Identify the type of legal document"""
        filename_lower = filename.lower()
        text_lower = text.lower()

        if 'constitution' in filename_lower:
            return 'constitution'
        elif 'ipc' in filename_lower or 'penal code' in text_lower:
            return 'criminal_code'
        elif 'crpc' in filename_lower or 'criminal procedure' in text_lower:
            return 'procedure_code'
        elif 'evidence' in filename_lower:
            return 'evidence_act'
        elif 'judgment' in text_lower or 'petitioner' in text_lower:
            return 'case_law'
        else:
            return 'legal_document' 
        
def sanitize_extracted_metadata(meta: Dict) -> Dict:
    def _ensure_list(v):
        if v is None:
            return []
        if isinstance(v, (list, tuple, set)):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            s = v.strip()
            if s == "":
                return []
            parts = re.split(r'\s*(?:,|;|and|\|)\s*', s)
            # keep numeric tokens (they may be valid sections).
            # If page number is present in metadata, drop tokens equal to that page (likely header/footer).
            page_str = str(meta.get('page')) if meta.get('page') is not None else None
            cleaned = []
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                if page_str and p == page_str:
                    # skip exact page number occurrences
                    continue
                cleaned.append(p)
            return cleaned
        return [str(v).strip()]

    def _norm_token_inner(s: str) -> str:
        return _norm_token(s) if callable(globals().get('_norm_token')) else re.sub(r'[^a-z0-9_]', '', str(s).lower().replace(' ', '_'))

    # Ensure basic list fields
    meta['extracted_sections'] = _ensure_list(meta.get('extracted_sections', []))
    meta['extracted_acts'] = _ensure_list(meta.get('extracted_acts', []))
    meta['legal_topics'] = _ensure_list(meta.get('legal_topics', []))

    # Normalize section tokens (use existing normalizer if present)
    norm_secs = []
    for s in meta['extracted_sections']:
        tok = str(s).strip()
        # try to keep section shape like "120B"
        tok = re.sub(r'[\s\.\)]+', '', tok)
        if tok:
           normalized = _norm_section_token(tok) if callable(globals().get('_norm_section_token')) else tok.upper()
           norm_secs.append(str(normalized).lower())
    meta['extracted_sections_norm'] = norm_secs

    # Normalize acts & topics
    meta['extracted_acts_norm'] = [_norm_token_inner(a).lower() for a in meta['extracted_acts']]
    meta['legal_topics_norm'] = [_norm_token_inner(t).lower() for t in meta['legal_topics']]

    # referenced_sections should be list of dicts like {"section": "...", "act": "..."}
    refs = meta.get('referenced_sections', [])
    if isinstance(refs, str):
        meta['referenced_sections'] = []
    elif isinstance(refs, list):
        cleaned = []
        for r in refs:
            if isinstance(r, dict) and 'section' in r:
                cleaned.append({'section': str(r.get('section')), 'act': r.get('act', '')})
        meta['referenced_sections'] = cleaned
    else:
        meta['referenced_sections'] = []

    # Filename/other canonical fields
    if 'filename_norm' not in meta:
        meta['filename_norm'] = _norm_token_inner(meta.get('source_file', meta.get('source', '')))

    # Ensure no empty-string leaves
    for k in ['extracted_sections', 'extracted_acts', 'legal_topics', 'extracted_sections_norm', 'extracted_acts_norm', 'legal_topics_norm']:
        if meta.get(k) is None:
            meta[k] = []

    return meta

def serialize_metadata_for_storage(meta: Dict) -> Dict:
    """
    Convert metadata values to Chroma-friendly primitive types.
    - Lists/tuples/sets -> comma-separated string
    - dicts -> JSON string
    - other -> str()
    Idempotent: safe to call on already-serialized metadata.
    """
    import json

    out: Dict = {}
    for k, v in (meta or {}).items():
        if v is None:
            continue
        # primitive ok
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
            continue

        # lists/tuples/sets -> join
        if isinstance(v, (list, tuple, set)):
            # preserve order, stringify items
            try:
                # ensure normalized fields are lowercased tokens in storage
                if k.endswith("_norm") or k in ("filename_norm",):
                    out[k] = ", ".join(str(x).strip().lower() for x in v)
                else:
                    out[k] = ", ".join(str(x) for x in v)
            except Exception:
                out[k] = json.dumps(list(v), ensure_ascii=False)
            continue

        # dict -> json
        if isinstance(v, dict):
            try:
                out[k] = json.dumps(v, ensure_ascii=False)
            except Exception:
                out[k] = str(v)
            continue

        # fallback: stringify
        out[k] = str(v)

    return out