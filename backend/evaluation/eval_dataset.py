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

from typing import List, Dict, Any
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

class LegalEvalDataset:
    """
    Collection of test questions for evaluating legal RAG systems.
    
    SIMPLE CONCEPT:
    This is like a comprehensive exam for your AI system covering
    different areas of law that your users commonly ask about.
    """
    
    def __init__(self):
        """Initialize the dataset with carefully crafted legal questions."""
        self.questions = self._create_evaluation_questions()
    
    def get_all_questions(self) -> List[EvaluationQuestion]:
        """Get all evaluation questions."""
        return self.questions
    
    def get_questions_by_category(self, category: str) -> List[EvaluationQuestion]:
        """Get questions from a specific legal category."""
        return [q for q in self.questions if q.category == category]
    
    def get_questions_by_difficulty(self, difficulty: str) -> List[EvaluationQuestion]:
        """Get questions of a specific difficulty level."""
        return [q for q in self.questions if q.difficulty == difficulty]
    
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
                explanation="Tests basic knowledge of most serious criminal offense punishment"
            ),
            
            EvaluationQuestion(
                id="criminal_002", 
                question="What is the difference between IPC Section 299 and 302?",
                expected_answer="Section 299 defines culpable homicide while Section 302 defines murder. Murder is culpable homicide with intention to cause death or knowledge that the act will likely cause death.",
                category="criminal_law",
                difficulty="medium", 
                keywords=["culpable homicide", "murder", "intention", "knowledge", "299", "302"],
                explanation="Tests understanding of related but distinct legal concepts"
            ),
            
            EvaluationQuestion(
                id="criminal_003",
                question="What are the essential elements of theft under IPC Section 378?",
                expected_answer="Essential elements of theft are: 1) Dishonest intention, 2) Taking of movable property, 3) Property belongs to another person, 4) Taking without consent, 5) Intention to permanently deprive the owner.",
                category="criminal_law",
                difficulty="hard",
                keywords=["dishonest intention", "movable property", "consent", "permanently deprive"],
                explanation="Tests detailed understanding of legal elements and requirements"
            ),
            
            # CONTRACT LAW QUESTIONS
            EvaluationQuestion(
                id="contract_001",
                question="What is a valid contract under the Indian Contract Act?",
                expected_answer="A valid contract requires: 1) Offer and acceptance, 2) Consideration, 3) Capacity to contract, 4) Free consent, 5) Lawful object, 6) Not expressly declared void.",
                category="contract_law",
                difficulty="easy", 
                keywords=["offer", "acceptance", "consideration", "capacity", "free consent", "lawful object"],
                explanation="Tests fundamental contract law principles"
            ),
            
            EvaluationQuestion(
                id="contract_002",
                question="What is the difference between void and voidable contracts?",
                expected_answer="Void contracts are invalid from the beginning and have no legal effect. Voidable contracts are valid until one party chooses to avoid them due to factors like coercion, fraud, or misrepresentation.",
                category="contract_law", 
                difficulty="medium",
                keywords=["void", "voidable", "invalid", "coercion", "fraud", "misrepresentation"],
                explanation="Tests understanding of contract validity concepts"
            ),
            
            # PROPERTY LAW QUESTIONS  
            EvaluationQuestion(
                id="property_001",
                question="What is the difference between movable and immovable property?",
                expected_answer="Immovable property includes land, buildings, and things attached to earth. Movable property includes all other property like goods, money, securities that can be moved.",
                category="property_law",
                difficulty="easy",
                keywords=["immovable", "land", "buildings", "movable", "goods", "securities"],
                explanation="Tests basic property classification knowledge"
            ),
            
            # CONSTITUTIONAL LAW QUESTIONS
            EvaluationQuestion(
                id="constitutional_001", 
                question="What are the fundamental rights under Article 14?",
                expected_answer="Article 14 guarantees the right to equality before law and equal protection of laws. It ensures that the state shall not deny any person equality before the law or equal protection of laws within Indian territory.",
                category="constitutional_law",
                difficulty="easy",
                keywords=["equality", "equal protection", "article 14", "fundamental rights"],
                explanation="Tests knowledge of basic constitutional rights"
            ),
            
            # COMPANY LAW QUESTIONS
            EvaluationQuestion(
                id="company_001",
                question="What is the minimum number of directors required for a private company?",
                expected_answer="Under the Companies Act 2013, a private company must have a minimum of 2 directors.",
                category="company_law", 
                difficulty="easy",
                keywords=["private company", "minimum", "2 directors", "companies act 2013"],
                explanation="Tests basic company law compliance requirements"
            ),
            
            # COMPLEX SCENARIO QUESTIONS
            EvaluationQuestion(
                id="scenario_001",
                question="If A promises to pay B Rs 10,000 if B's house burns down, is this a valid contract?",
                expected_answer="This is not a valid contract as it lacks consideration from B's side. B is not doing anything or promising anything in return. It appears more like a promise of gift or insurance without premium.",
                category="contract_law",
                difficulty="hard", 
                keywords=["consideration", "valid contract", "gift", "insurance", "premium"],
                explanation="Tests application of contract principles to practical scenarios"
            ),
            
            # PROCEDURAL LAW QUESTIONS
            EvaluationQuestion(
                id="procedure_001",
                question="What is the limitation period for filing a suit for recovery of money?",
                expected_answer="Under the Limitation Act, the limitation period for a suit for recovery of money is 3 years from the date when the right to receive the money accrues.",
                category="procedural_law",
                difficulty="medium",
                keywords=["limitation period", "3 years", "recovery of money", "limitation act"],
                explanation="Tests knowledge of procedural timelines and requirements"
            ),
            
            # EVIDENCE LAW QUESTIONS
            EvaluationQuestion(
                id="evidence_001",
                question="What is the difference between direct and circumstantial evidence?",
                expected_answer="Direct evidence directly proves a fact without need for inference (like eyewitness testimony). Circumstantial evidence requires inference to establish a fact (like finding defendant's fingerprints at crime scene).",
                category="evidence_law",
                difficulty="medium", 
                keywords=["direct evidence", "circumstantial evidence", "inference", "eyewitness", "fingerprints"],
                explanation="Tests understanding of evidence types and their probative value"
            ),
            
            # FAMILY LAW QUESTIONS
            EvaluationQuestion(
                id="family_001",
                question="Under which law are Hindu marriages governed in India?",
                expected_answer="Hindu marriages in India are governed by the Hindu Marriage Act, 1955, which applies to Hindus, Buddhists, Sikhs, and Jains.",
                category="family_law",
                difficulty="easy",
                keywords=["hindu marriage act", "1955", "hindus", "buddhists", "sikhs", "jains"],
                explanation="Tests knowledge of personal law applicability"
            ),
            
            # LABOR LAW QUESTIONS
            EvaluationQuestion(
                id="labor_001",
                question="What is the maximum working hours per week under the Factories Act?",
                expected_answer="Under the Factories Act 1948, the maximum working hours are 48 hours per week and 9 hours per day for adults.",
                category="labor_law", 
                difficulty="easy",
                keywords=["48 hours", "week", "9 hours", "day", "factories act", "1948"],
                explanation="Tests knowledge of worker protection laws"
            ),
            
            # INTELLECTUAL PROPERTY QUESTIONS
            EvaluationQuestion(
                id="ip_001",
                question="What is the duration of copyright protection in India?",
                expected_answer="In India, copyright protection generally lasts for the lifetime of the author plus 60 years. For anonymous works, it lasts 60 years from publication.",
                category="intellectual_property",
                difficulty="medium",
                keywords=["copyright", "lifetime plus 60 years", "anonymous works", "60 years", "publication"],
                explanation="Tests knowledge of IP protection duration"
            ),
            
            # TAX LAW QUESTIONS  
            EvaluationQuestion(
                id="tax_001",
                question="What is the current basic exemption limit for individual income tax?",
                expected_answer="For Assessment Year 2023-24, the basic exemption limit for individuals below 60 years is Rs 2.5 lakh under the old tax regime and Rs 3 lakh under the new tax regime.",
                category="tax_law",
                difficulty="easy", 
                keywords=["exemption limit", "2.5 lakh", "3 lakh", "old regime", "new regime"],
                explanation="Tests current tax law knowledge (may need updates)"
            ),
            
            # BANKING LAW QUESTIONS
            EvaluationQuestion(
                id="banking_001", 
                question="What is a negotiable instrument under the Negotiable Instruments Act?",
                expected_answer="A negotiable instrument is a document that guarantees payment of money, can be transferred from one person to another, and includes promissory notes, bills of exchange, and cheques.",
                category="banking_law",
                difficulty="medium",
                keywords=["negotiable instrument", "promissory notes", "bills of exchange", "cheques", "transferable"],
                explanation="Tests understanding of commercial law instruments"
            ),
            
            # ENVIRONMENTAL LAW QUESTIONS
            EvaluationQuestion(
                id="environment_001",
                question="What is the principle of 'polluter pays' in environmental law?",
                expected_answer="The 'polluter pays' principle means that the person or entity responsible for pollution should bear the cost of measures to prevent, control, and remedy environmental damage.",
                category="environmental_law", 
                difficulty="medium",
                keywords=["polluter pays", "environmental damage", "prevention", "control", "remedy"],
                explanation="Tests understanding of environmental law principles"
            ),
            
            # COMPLEX LEGAL REASONING QUESTIONS
            EvaluationQuestion(
                id="reasoning_001",
                question="Can a minor enter into a contract for necessities of life?",
                expected_answer="Yes, a minor can enter into a contract for necessities of life like food, clothing, shelter, and education. Such contracts are valid and enforceable, but the minor is only liable to pay a reasonable price.",
                category="contract_law",
                difficulty="hard",
                keywords=["minor", "necessities", "food", "clothing", "shelter", "reasonable price"],
                explanation="Tests application of capacity rules to practical situations"
            ),
            
            # CONSTITUTIONAL INTERPRETATION QUESTIONS
            EvaluationQuestion(
                id="constitutional_002",
                question="What is the doctrine of basic structure in Indian constitutional law?",
                expected_answer="The basic structure doctrine holds that Parliament cannot amend the Constitution in a way that destroys its basic structure or essential features, even through constitutional amendments.",
                category="constitutional_law", 
                difficulty="hard",
                keywords=["basic structure", "parliament", "constitutional amendments", "essential features"],
                explanation="Tests understanding of advanced constitutional principles"
            ),
            
            # COMPARATIVE LAW QUESTIONS
            EvaluationQuestion(
                id="comparative_001",
                question="What is the difference between common law and civil law systems?", 
                expected_answer="Common law systems rely on judicial precedents and case law (like India, UK, US). Civil law systems rely primarily on written codes and statutes (like France, Germany). India follows a mixed system.",
                category="jurisprudence",
                difficulty="medium",
                keywords=["common law", "civil law", "precedents", "case law", "written codes", "mixed system"],
                explanation="Tests understanding of legal system types and India's position"
            )
        ]
        
        return questions

# Global instance for use across the application
legal_eval_dataset = LegalEvalDataset()