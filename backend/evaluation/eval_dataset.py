"""
Legal RAG Evaluation Dataset

SIMPLE PURPOSE:
This file contains test questions with known correct answers.
Think of it like a standardized test for your legal AI system.

WHY WE NEED THIS:
- To measure if our system is getting better or worse over time
- To test changes before deploying them
- To show interviewers concrete quality metrics

HOW IT WORKS:
1. We define questions lawyers commonly ask
2. We provide the correct/expected answers
3. We run our RAG system on these questions  
4. We compare our system's answers to the correct ones
5. We get quality scores (like test grades)
"""

import json
import pathlib
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class EvaluationQuestion:
    """
    A single test question with its expected answer.
    
    Think of this like one question on a standardized test:
    - The question students need to answer
    - The correct answer they should give
    - Extra context about why this question matters
    """
    id: str                          # Unique identifier (like "question_1")
    question: str                    # The question to ask our system
    expected_answer: str             # What the correct answer should be
    category: str                    # Type of legal question (contracts, criminal, etc.)
    difficulty: str                  # How hard this question is (easy, medium, hard)
    keywords: List[str]              # Important words that should appear in good answers
    explanation: str                 # Why this question tests something important
    ground_truth_doc_ids: Optional[List[str]] = None


class LegalEvalDataset:
    """
    Collection of test questions for evaluating legal RAG systems.
    
    SIMPLE CONCEPT:
    This is like a comprehensive exam for your AI system covering
    different areas of law that your users commonly ask about.
    """
    
    def __init__(self, question_type: str):
        """Initialize the dataset with carefully crafted legal questions."""
        self.question_type = question_type.lower()
        self.questions = self.get_all_questions()

    def get_all_questions(self) -> List[EvaluationQuestion]:
        """Get all evaluation questions."""
        if self.question_type == 'hard':
            return self._create_evaluation_questions_hard()
        return self._create_evaluation_questions()
    
    def get_questions_by_category(self, category: str) -> List[EvaluationQuestion]:
        """Get questions from a specific legal category."""
        return [q for q in self.questions if q.category == category]
    
    def get_questions_by_difficulty(self, difficulty: str) -> List[EvaluationQuestion]:
        """Get questions of a specific difficulty level."""
        return [q for q in self.questions if q.difficulty == difficulty]
    
    def build_evaluation_questions(self, difficulty: Optional[str] = None) -> List[EvaluationQuestion]:
        """
        Build and return evaluation questions.

        Parameters:
        - difficulty: Optional[str] = "easy" | "hard" | None
          - "easy": return only existing static easy questions
          - "hard": return only the generated (persisted) hard questions
          - None: return combined set (static + generated hard)
        """
        existing_questions = self._create_evaluation_questions()

        if difficulty == "easy":
            return [q for q in existing_questions if q.difficulty == "easy"]

        if difficulty == "hard":
            return self._load_or_generate_hard_questions()

        # default: combined (avoid id collisions)
        combined = list(existing_questions)
        existing_ids = {q.id for q in combined}
        hard_generated = self._load_or_generate_hard_questions()
        for h in hard_generated:
            if h.id not in existing_ids:
                combined.append(h)
        return combined

    def _load_or_generate_hard_questions(self) -> List[EvaluationQuestion]:
        """Load persisted generated hard questions or deterministically create+persist them."""
        generated_path = pathlib.Path(__file__).resolve().parent / "generated_hard_questions.json"

        def _make_question_from_stem(i: int, stem: str, filename: str) -> Dict[str, Any]:
            words = re.split(r"[_\-\s]", stem)
            sample_kw = [w for w in words if len(w) > 3][:4] or words[:1]

            def _guess_category_from_name(s: str) -> str:
                s = s.lower()
                if "constitution" in s: return "constitutional_law"
                if "evidence" in s: return "evidence_law"
                if "contract" in s or "contracts" in s: return "contract_law"
                if "procedure" in s or "crpc" in s: return "procedural_law"
                if "penal" in s or "ipc" in s or "penalties" in s: return "criminal_law"
                if "tort" in s or "negligence" in s: return "tort_law"
                if "admin" in s or "administrative" in s: return "administrative_law"
                if "tax" in s: return "tax_law"
                if "civil" in s or "procedure" in s: return "civil_procedure"
                return "general_law"
            
            category = _guess_category_from_name(stem)

            templates = {
                "constitutional_law": f"When can {sample_kw[0]} be limited under constitutional law? Give the tests and leading exceptions.",
                "evidence_law": f"When is evidence from {sample_kw[0]} excluded and what tests determine admissibility?",
                "contract_law": f"When will a court set aside a contract related to {sample_kw[0]} for unconscionability or undue influence?",
                "procedural_law": f"What procedural safeguards apply in cases involving {sample_kw[0]} and when can detention be extended?",
                "criminal_law": f"What mens rea and actus reus requirements are necessary to convict under provisions related to {sample_kw[0]}?",
                "tort_law": f"How is causation established where {sample_kw[0]} contributes alongside other causes?",
                "administrative_law": f"When can an administrative decision about {sample_kw[0]} be quashed for being ultra vires?",
                "tax_law": f"What are the tests to decide whether a levy related to {sample_kw[0]} is a tax or a regulatory fee?",
                "civil_procedure": f"Can confidentiality over {sample_kw[0]} be preserved in public litigation and what mechanisms exist?",
                "general_law": f"What difficult legal issues arise in relation to {sample_kw[0]}, and what authorities govern them?"
            }

            q_text = templates.get(category, templates["general_law"])
            expected = f"Refer to {filename} for the authoritative provision/explanation."
            
            return {
                "id": f"auto_hard_{i:03d}",
                "question": q_text,
                "expected_answer": expected,
                "category": category,
                "difficulty": "hard",
                "keywords": sample_kw,
                "explanation": f"Auto-generated hard question based on document {filename}",
                "ground_truth_doc_ids": [filename],
            }

        # load if exists
        if generated_path.exists():
            try:
                with generated_path.open("r", encoding="utf-8") as fh:
                    generated = json.load(fh)
                return [EvaluationQuestion(**g) for g in generated]
            except Exception:
                # fall back to regeneration if load fails
                pass

        # otherwise generate deterministically from backend/documents/*.pdf (sorted order)
        try:
            doc_root = pathlib.Path(__file__).resolve().parents[1] / "documents"
            pdfs = sorted(p.name for p in doc_root.glob("*.pdf"))
        except Exception:
            pdfs = []

        generated_list: List[Dict[str, Any]] = []
        max_auto = 30
        i = 1
        for fname in pdfs:
            if i > max_auto:
                break
            g = _make_question_from_stem(i, pathlib.Path(fname).stem, fname)
            generated_list.append(g)
            i += 1

        # persist for reproducibility
        try:
            with generated_path.open("w", encoding="utf-8") as fh:
                json.dump(generated_list, fh, ensure_ascii=False, indent=2)
        except Exception:
            # non-fatal: proceed without persistence
            pass

        return [EvaluationQuestion(**g) for g in generated_list]

    def _create_evaluation_questions(self) -> List[EvaluationQuestion]:
        """
        Create the actual test questions.
        
        IMPORTANT: These are based on common legal questions that:
        1. Indian lawyers frequently ask
        2. Have clear, factual answers
        3. Test different aspects of legal knowledge
        4. Range from simple to complex
        """
        
        questions = [
            # CRIMINAL LAW QUESTIONS (IPC Sections)
            EvaluationQuestion(
                id="criminal_001",
                question="What is the punishment for murder under IPC Section 302?",
                expected_answer="Under IPC Section 302, the punishment for murder is death or imprisonment for life, and shall also be liable to fine.",
                category="criminal_law", 
                difficulty="easy",
                keywords=["death", "life imprisonment", "fine", "section 302", "murder"],
                explanation="Tests basic knowledge of most serious criminal offense punishment",
                ground_truth_doc_ids=["repealedfileopen.pdf"]
            ),

            EvaluationQuestion(
                id="criminal_002",
                question="What are the essential elements of theft under IPC Section 378?",
                expected_answer="Essential elements of theft are: 1) Dishonest intention, 2) Taking of movable property, 3) Property belongs to another person, 4) Taking without consent, 5) Intention to permanently deprive the owner.",
                category="criminal_law",
                difficulty="hard",
                keywords=["dishonest intention", "movable property", "consent", "permanently deprive"],
                explanation="Tests detailed understanding of legal elements and requirements",
                ground_truth_doc_ids=["repealedfileopen.pdf"]
            ),

            EvaluationQuestion(
                id="criminal_003",
                question="What is the definition of criminal conspiracy under IPC Section 120A?",
                expected_answer="Section 120A of IPC defines criminal conspiracy as when two or more persons agree to do, or cause to be done, an illegal act, or an act which is not illegal by illegal means.",
                category="criminal_law",
                difficulty="medium",
                keywords=["criminal conspiracy", "agreement", "illegal act", "section 120A"],
                explanation="Tests knowledge of criminal conspiracy provisions.",
                ground_truth_doc_ids=["repealedfileopen.pdf"]
            ),

            # PROCEDURAL LAW QUESTIONS (CrPC)
            EvaluationQuestion(
                id="procedure_001",
                question="What does Section 125 of the Code of Criminal Procedure provide for?",
                expected_answer="Section 125 empowers a Magistrate to order maintenance for wives, children, and parents if a person with sufficient means neglects or refuses to maintain them.",
                category="procedural_law",
                difficulty="medium",
                keywords=["CrPC", "Section 125", "maintenance", "wives", "children", "parents"],
                explanation="Tests knowledge of social justice provisions under procedural law.",
                ground_truth_doc_ids=["the_code_of_criminal_procedure,_1973.pdf"]
            ),

            EvaluationQuestion(
                id="procedure_002",
                question="What does Section 41 of the Code of Criminal Procedure state about police arrest without warrant?",
                expected_answer="Section 41 CrPC empowers police to arrest a person without warrant in certain circumstances, such as when a person commits a cognizable offence in their presence, or is reasonably suspected of being involved in one.",
                category="procedural_law",
                difficulty="medium",
                keywords=["CrPC", "Section 41", "arrest", "police", "warrant"],
                explanation="Tests understanding of arrest powers under CrPC.",
                ground_truth_doc_ids=["the_code_of_criminal_procedure,_1973.pdf"]
            ),

            EvaluationQuestion(
                id="procedure_003",
                question="What remedy does CrPC Section 154 provide?",
                expected_answer="Section 154 CrPC provides that every information relating to the commission of a cognizable offence, if given orally to an officer in charge of a police station, shall be reduced to writing and is known as an FIR (First Information Report).",
                category="procedural_law",
                difficulty="easy",
                keywords=["CrPC", "Section 154", "FIR", "cognizable offence"],
                explanation="Tests knowledge of the process of lodging FIRs.",
                ground_truth_doc_ids=["the_code_of_criminal_procedure,_1973.pdf"]
            ),

            # CONSTITUTIONAL LAW QUESTIONS
            EvaluationQuestion(
                id="constitutional_001",
                question="What does Article 14 of the Indian Constitution guarantee?",
                expected_answer="Article 14 guarantees the right to equality before law and equal protection of laws within Indian territory.",
                category="constitutional_law",
                difficulty="easy",
                keywords=["equality", "equal protection", "article 14", "fundamental rights"],
                explanation="Tests knowledge of basic constitutional rights",
                ground_truth_doc_ids=["constitution.pdf"]
            ),

            EvaluationQuestion(
                id="constitutional_002",
                question="What remedy does Article 32 of the Indian Constitution provide?",
                expected_answer="Article 32 provides the right to move the Supreme Court for enforcement of fundamental rights and empowers the Court to issue writs.",
                category="constitutional_law",
                difficulty="medium",
                keywords=["article 32", "remedy", "supreme court", "writs"],
                explanation="Tests knowledge of enforcement of fundamental rights.",
                ground_truth_doc_ids=["constitution.pdf"]
            ),

            EvaluationQuestion(
                id="constitutional_003",
                question="What does Article 21 of the Indian Constitution guarantee?",
                expected_answer="Article 21 guarantees protection of life and personal liberty, stating that no person shall be deprived of his life or personal liberty except according to procedure established by law.",
                category="constitutional_law",
                difficulty="easy",
                keywords=["article 21", "life", "liberty", "procedure established by law"],
                explanation="Tests knowledge of the right to life and liberty.",
                ground_truth_doc_ids=["constitution.pdf"]
            ),

            EvaluationQuestion(
                id="constitutional_004",
                question="What is the Directive Principle under Article 39A of the Indian Constitution?",
                expected_answer="Article 39A directs the State to secure equal justice and provide free legal aid, ensuring that opportunities for securing justice are not denied to any citizen by reason of economic or other disabilities.",
                category="constitutional_law",
                difficulty="medium",
                keywords=["article 39A", "equal justice", "free legal aid", "directive principles"],
                explanation="Tests knowledge of directive principles of state policy.",
                ground_truth_doc_ids=["constitution.pdf"]
            ),

            EvaluationQuestion(
                id="constitutional_005",
                question="What are the Fundamental Duties under Article 51A of the Indian Constitution?",
                expected_answer="Article 51A lists fundamental duties of citizens, including respecting the Constitution, cherishing noble ideals of the freedom struggle, protecting sovereignty, defending the country, promoting harmony, protecting the environment, and developing scientific temper.",
                category="constitutional_law",
                difficulty="hard",
                keywords=["article 51A", "fundamental duties", "citizens"],
                explanation="Tests knowledge of citizen duties in the Constitution.",
                ground_truth_doc_ids=["constitution.pdf"]
            ),

            EvaluationQuestion(
                id="constitutional_006",
                question="What is the doctrine of basic structure in Indian constitutional law?",
                expected_answer="The basic structure doctrine holds that Parliament cannot amend the Constitution in a way that destroys its basic structure or essential features, even through constitutional amendments.",
                category="constitutional_law",
                difficulty="hard",
                keywords=["basic structure", "parliament", "constitutional amendments", "essential features"],
                explanation="Tests understanding of advanced constitutional principles",
                ground_truth_doc_ids=["constitution.pdf"]
            ),

            # CRPC PROCEDURAL RIGHTS
            EvaluationQuestion(
                id="procedure_004",
                question="What does Section 167 of the CrPC provide regarding detention?",
                expected_answer="Section 167 of CrPC provides that an accused person cannot be detained by police beyond 24 hours without being produced before a Magistrate. Magistrates can authorize further detention up to 15 days, and in serious cases, up to 60 or 90 days depending on the offence.",
                category="procedural_law",
                difficulty="hard",
                keywords=["CrPC", "section 167", "detention", "magistrate"],
                explanation="Tests knowledge of procedural safeguards against unlawful detention.",
                ground_truth_doc_ids=["the_code_of_criminal_procedure,_1973.pdf"]
            ),

            EvaluationQuestion(
                id="procedure_005",
                question="What does Section 313 of the CrPC provide for?",
                expected_answer="Section 313 CrPC empowers the Court to question the accused generally on the case after the prosecution evidence is complete, to enable them to explain any circumstances appearing in evidence against them.",
                category="procedural_law",
                difficulty="medium",
                keywords=["CrPC", "Section 313", "accused", "examination"],
                explanation="Tests knowledge of fair trial rights under CrPC.",
                ground_truth_doc_ids=["the_code_of_criminal_procedure,_1973.pdf"]
            ),

            EvaluationQuestion(
                id="procedure_006",
                question="What does Section 320 of the CrPC provide for?",
                expected_answer="Section 320 CrPC provides a list of offences that may be compounded, i.e., settled between parties with or without permission of the court, such as certain cases of hurt, defamation, adultery, etc.",
                category="procedural_law",
                difficulty="hard",
                keywords=["CrPC", "Section 320", "compounding", "offences"],
                explanation="Tests knowledge of compounding of offences.",
                ground_truth_doc_ids=["the_code_of_criminal_procedure,_1973.pdf"]
            )
        ]

        return questions
    
    def _create_evaluation_questions_hard(self) -> List[EvaluationQuestion]:
        """Create hard evaluation questions (if needed separately)."""
        questions = [
            # 1 - Ambiguity between IPC & CrPC sections
            EvaluationQuestion(
                id="hard_criminal_001",
                question="When a court order cites only 'Section 302' without mentioning the Act, how should one determine whether it refers to IPC Section 302 (murder) or CrPC Section 302 (permission to conduct prosecution)?",
                expected_answer="The correct interpretation depends on the Act context. In substantive criminal law, Section 302 IPC refers to punishment for murder. In procedural contexts, Section 302 CrPC empowers a magistrate to permit prosecution. The court's context and statutory reference control which Act applies.",
                category="criminal_law",
                difficulty="hard",
                keywords=["302", "IPC", "CrPC", "ambiguity", "context"],
                explanation="Tests ability to disambiguate overlapping section numbers across different Acts.",
                ground_truth_doc_ids=["repealedfileopen.pdf", "the_code_of_criminal_procedure,_1973.pdf"]
            ),

            # 2 - Mens rea edge case under theft
            EvaluationQuestion(
                id="hard_criminal_002",
                question="If a person picks up another's wallet thinking it is his own, does this amount to theft under IPC Section 378?",
                expected_answer="No theft is committed if there is no dishonest intention. IPC 378 requires dishonest intention at the time of taking. Mistaken belief of ownership negates mens rea, though liability may arise if, after realizing, the person continues to retain it dishonestly.",
                category="criminal_law",
                difficulty="hard",
                keywords=["theft", "mens rea", "dishonest intention", "mistaken belief"],
                explanation="Tests edge cases of mens rea in theft.",
                ground_truth_doc_ids=["repealedfileopen.pdf"]
            ),

            # 3 - Exception clause
            EvaluationQuestion(
                id="hard_criminal_003",
                question="Under IPC Section 300, culpable homicide is not murder if the act is done without premeditation in a sudden fight. How should courts decide when a fight is 'sudden'?",
                expected_answer="Courts examine whether there was premeditation or undue advantage taken. If the altercation was spontaneous without planning, and the accused did not act cruelly, Exception 4 to Section 300 applies, reducing liability to culpable homicide under Section 304.",
                category="criminal_law",
                difficulty="hard",
                keywords=["murder", "culpable homicide", "sudden fight", "exception"],
                explanation="Tests application of statutory exceptions in homicide cases.",
                ground_truth_doc_ids=["repealedfileopen.pdf"]
            ),

            # 4 - Cross-section dependency
            EvaluationQuestion(
                id="hard_criminal_004",
                question="How do IPC Sections 120A and 120B on criminal conspiracy interact with Section 107 on abetment when the agreement itself is incomplete?",
                expected_answer="IPC 120A defines conspiracy as agreement to commit an illegal act. Section 120B punishes such conspiracy. If the conspiracy is incomplete, liability may still arise under Section 107 for abetment. Courts determine whether overt acts or agreement suffice.",
                category="criminal_law",
                difficulty="hard",
                keywords=["120A", "120B", "criminal conspiracy", "abetment"],
                explanation="Tests interaction of conspiracy and abetment provisions.",
                ground_truth_doc_ids=["repealedfileopen.pdf"]
            ),

            # 5 - Retrospective application
            EvaluationQuestion(
                id="hard_criminal_005",
                question="Can an amendment to IPC Section 124A (sedition) apply to speeches made before the amendment date?",
                expected_answer="No. Criminal liability cannot be retrospectively imposed under Article 20(1) of the Constitution. An amendment enhancing penalty or widening scope applies prospectively unless expressly stated, but Article 20(1) bars ex post facto criminal laws.",
                category="constitutional_law",
                difficulty="hard",
                keywords=["sedition", "124A", "retrospective", "Article 20"],
                explanation="Tests constitutional bar on ex post facto laws.",
                ground_truth_doc_ids=["repealedfileopen.pdf", "constitution.pdf"]
            ),

            # 6 - Procedural timing trap
            EvaluationQuestion(
                id="hard_procedure_001",
                question="Under CrPC Section 167, if police fail to file a charge sheet within 90 days for an offence punishable with death, what happens if the accused does not apply for bail immediately?",
                expected_answer="Failure to file within 90 days grants an indefeasible right to default bail under Section 167(2). However, if the accused does not apply before filing of the charge sheet, the right lapses once the charge sheet is filed.",
                category="procedural_law",
                difficulty="hard",
                keywords=["default bail", "167", "90 days", "charge sheet"],
                explanation="Tests nuanced understanding of procedural timelines and rights.",
                ground_truth_doc_ids=["the_code_of_criminal_procedure,_1973.pdf"]
            ),

            # 7 - Cognizability & compoundability
            EvaluationQuestion(
                id="hard_procedure_002",
                question="Is an offence under IPC Section 498A (cruelty by husband or relatives) compoundable under Section 320 CrPC?",
                expected_answer="Originally non-compoundable, the Supreme Court allowed quashing under Section 482 CrPC in cases of settlement. Statutorily, Section 498A is not in the compoundable list under Section 320. Thus, compounding is not permitted without High Court intervention.",
                category="procedural_law",
                difficulty="hard",
                keywords=["498A", "compoundable", "320", "482 CrPC"],
                explanation="Tests understanding of compounding vs quashing distinctions.",
                ground_truth_doc_ids=["repealedfileopen.pdf", "the_code_of_criminal_procedure,_1973.pdf"]
            ),

            # 8 - Interpretive ambiguity
            EvaluationQuestion(
                id="hard_constitutional_001",
                question="How does Article 14’s 'reasonable classification' test reconcile with affirmative action under Article 15(4)?",
                expected_answer="Article 14 allows classification if intelligible differentia and rational nexus exist. Article 15(4) explicitly authorizes affirmative action for backward classes, treated as a reasonable classification consistent with Article 14.",
                category="constitutional_law",
                difficulty="hard",
                keywords=["Article 14", "Article 15", "reasonable classification", "affirmative action"],
                explanation="Tests interpretation of equality vs affirmative action.",
                ground_truth_doc_ids=["constitution.pdf"]
            ),

            # 9 - Multi-section combo
            EvaluationQuestion(
                id="hard_criminal_006",
                question="How do IPC Sections 34 (common intention) and 149 (unlawful assembly) differ when multiple persons commit an offence?",
                expected_answer="Section 34 applies when several persons act with common intention, regardless of assembly size. Section 149 requires an unlawful assembly of five or more. Courts decide based on participation, numbers, and shared object.",
                category="criminal_law",
                difficulty="hard",
                keywords=["common intention", "unlawful assembly", "34", "149"],
                explanation="Tests differentiation between group liability provisions.",
                ground_truth_doc_ids=["repealedfileopen.pdf"]
            ),

            # 10 - Counterfactual
            EvaluationQuestion(
                id="hard_criminal_007",
                question="If A aims a gun at B intending to kill, but B dies of a heart attack before A fires, is A guilty of murder under IPC Section 302?",
                expected_answer="No murder is committed because the act did not cause death. A may be liable for attempt under Section 307 IPC, but causation under Section 302 fails.",
                category="criminal_law",
                difficulty="hard",
                keywords=["attempt", "murder", "302", "307", "causation"],
                explanation="Tests causation requirement in homicide.",
                ground_truth_doc_ids=["repealedfileopen.pdf"]
            ),

            # 11 - Procedural cross-reference
            EvaluationQuestion(
                id="hard_procedure_003",
                question="Under CrPC Section 313, can an accused remain silent during examination without adverse inference?",
                expected_answer="Yes. The accused has a right to silence. Section 313 enables explanation but refusal cannot be the sole basis for conviction. However, adverse inference may be drawn if prosecution evidence is strong.",
                category="procedural_law",
                difficulty="hard",
                keywords=["313", "right to silence", "adverse inference"],
                explanation="Tests limits of accused’s examination rights.",
                ground_truth_doc_ids=["the_code_of_criminal_procedure,_1973.pdf"]
            ),

            # 12 - Extraterritoriality
            EvaluationQuestion(
                id="hard_criminal_008",
                question="Does IPC Section 4 extend jurisdiction to offences committed abroad by Indian citizens?",
                expected_answer="Yes, IPC Section 4 extends jurisdiction to offences committed outside India by Indian citizens, or on Indian-registered ships and aircraft. Enforcement requires cooperation and sanction.",
                category="criminal_law",
                difficulty="hard",
                keywords=["extraterritorial", "jurisdiction", "Section 4"],
                explanation="Tests understanding of jurisdiction extension.",
                ground_truth_doc_ids=["repealedfileopen.pdf"]
            ),

            # 13 - Constitutional ambiguity
            EvaluationQuestion(
                id="hard_constitutional_002",
                question="Can the right to life under Article 21 be suspended during an emergency under Article 359?",
                expected_answer="Earlier, during Emergency (ADM Jabalpur), Article 21 was suspended. Post 44th Amendment, Article 21 cannot be suspended even under Article 359.",
                category="constitutional_law",
                difficulty="hard",
                keywords=["Article 21", "Article 359", "emergency", "suspension"],
                explanation="Tests constitutional evolution under emergencies.",
                ground_truth_doc_ids=["constitution.pdf", "constitution.pdf"]
            ),

            # 14 - Procedural trap
            EvaluationQuestion(
                id="hard_procedure_004",
                question="If a Magistrate takes cognizance without proper sanction under CrPC Section 197, is the trial void?",
                expected_answer="Proceedings without sanction under Section 197 are invalid. However, if sanction is granted later before judgment, the defect may be cured.",
                category="procedural_law",
                difficulty="hard",
                keywords=["197", "sanction", "cognizance", "public servant"],
                explanation="Tests procedural safeguards for public servants.",
                ground_truth_doc_ids=["the_code_of_criminal_procedure,_1973.pdf"]
            ),

            # 15 - Overlap IPC vs Constitution
            EvaluationQuestion(
                id="hard_constitutional_003",
                question="How does IPC Section 124A (sedition) reconcile with Article 19(1)(a) guaranteeing freedom of speech?",
                expected_answer="Sedition limits free speech. Courts read it narrowly under Article 19(2), punishing only speech inciting violence or public disorder, not mere criticism of the government.",
                category="constitutional_law",
                difficulty="hard",
                keywords=["sedition", "124A", "Article 19", "free speech"],
                explanation="Tests balancing of penal provisions with constitutional rights.",
                ground_truth_doc_ids=["repealedfileopen.pdf", "constitution.pdf"]
            ),

            # 16 - Evidentiary burden
            EvaluationQuestion(
                id="hard_evidence_001",
                question="In a case relying on circumstantial evidence under IPC Section 302, what is the standard for conviction?",
                expected_answer="Circumstantial evidence must form a complete chain consistent only with guilt and exclude every hypothesis of innocence.",
                category="evidence_law",
                difficulty="hard",
                keywords=["circumstantial evidence", "murder", "302"],
                explanation="Tests evidentiary sufficiency standards.",
                ground_truth_doc_ids=["repealedfileopen.pdf"]
            ),

            # 17 - Maintenance edge case
            EvaluationQuestion(
                id="hard_procedure_005",
                question="Under CrPC Section 125, can a divorced Muslim woman claim maintenance after iddat period?",
                expected_answer="The Supreme Court in Shah Bano held yes under Section 125. Later the Muslim Women Act restricted it, but subsequent rulings allowed fair provision beyond iddat. Thus, maintenance may extend beyond iddat.",
                category="procedural_law",
                difficulty="hard",
                keywords=["125", "maintenance", "divorced Muslim woman"],
                explanation="Tests social justice vs personal law conflicts.",
                ground_truth_doc_ids=["the_code_of_criminal_procedure,_1973.pdf"]
            ),

            # 18 - Counterfactual on attempt
            EvaluationQuestion(
                id="hard_criminal_009",
                question="If A mixes poison in food but the victim does not consume it, is A guilty of attempt to murder?",
                expected_answer="Yes, A is guilty under Section 307 IPC. The act towards commission, even without consumption, constitutes attempt.",
                category="criminal_law",
                difficulty="hard",
                keywords=["attempt", "poison", "307"],
                explanation="Tests limits of attempt liability.",
                ground_truth_doc_ids=["repealedfileopen.pdf"]
            ),

            # 19 - Procedural vs substantive conflict
            EvaluationQuestion(
                id="hard_criminal_010",
                question="If an accused is acquitted under IPC due to benefit of doubt, can the State appeal under CrPC Section 378?",
                expected_answer="Yes, Section 378 CrPC allows the State to appeal against acquittal, subject to leave of the High Court.",
                category="procedural_law",
                difficulty="hard",
                keywords=["acquittal", "appeal", "378 CrPC"],
                explanation="Tests interplay of substantive acquittal with procedural appeal.",
                ground_truth_doc_ids=["the_code_of_criminal_procedure,_1973.pdf"]
            ),

            # 20 - Basic structure doctrine
            EvaluationQuestion(
                id="hard_constitutional_004",
                question="Can Parliament amend the Constitution to abrogate judicial review under Articles 32 and 226?",
                expected_answer="No. Judicial review is part of the basic structure. Any amendment removing it would be unconstitutional.",
                category="constitutional_law",
                difficulty="hard",
                keywords=["judicial review", "basic structure", "Article 32", "Article 226"],
                explanation="Tests core constitutional limitation on amendment power.",
                ground_truth_doc_ids=["constitution.pdf", "constitution.pdf"]
            )
        ]
        return questions

    

