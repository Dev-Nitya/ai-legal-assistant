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

# Global instance for use across the application
legal_eval_dataset = LegalEvalDataset()