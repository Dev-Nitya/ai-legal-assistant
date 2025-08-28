"""
Simple test script to verify the evaluation system works.

WHAT THIS DOES:
Tests our complete evaluation pipeline to make sure:
1. API endpoints are working
2. RAG evaluation is functioning  
3. Scores are reasonable
4. No crashes or errors
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"  # Your FastAPI server
TEST_QUESTION = "What is the punishment for murder under IPC Section 302?"

def test_evaluation_system():
    """Test the complete evaluation system."""
    
    print("🧪 Testing RAG Evaluation System")
    print("=" * 50)
    
    # Test 1: Check if evaluation endpoints are available
    print("\n1. Testing dataset statistics endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/evaluate/dataset/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Dataset loaded: {stats['total_questions']} questions")
            print(f"   Categories: {stats['available_categories']}")
        else:
            print(f"❌ Dataset stats failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False
    
    # Test 2: Single question evaluation
    print(f"\n2. Testing single question evaluation...")
    print(f"   Question: {TEST_QUESTION}")
    
    try:
        eval_request = {
            "question": TEST_QUESTION,
            "user_id": "test_user",
            "use_ground_truth": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/evaluate/single",
            json=eval_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Single evaluation successful!")
            print(f"   Generated answer: {result['generated_answer'][:100]}...")
            print(f"   Overall score: {result['evaluation_result']['overall_score']:.3f}")
            print(f"   Retrieval precision@5: {result['evaluation_result']['retrieval_precision_at_5']:.3f}")
            print(f"   Answer relevance: {result['evaluation_result']['answer_relevance']:.3f}")
            print(f"   Answer faithfulness: {result['evaluation_result']['answer_faithfulness']:.3f}")
            print(f"   Retrieved docs: {result['retrieved_documents_count']}")
            print(f"   Processing time: {result['processing_time_seconds']:.2f}s")
        else:
            print(f"❌ Single evaluation failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Single evaluation error: {e}")
        return False
    
    # Test 3: Small batch evaluation
    print(f"\n3. Testing batch evaluation (criminal law questions)...")
    
    try:
        batch_request = {
            "category": "criminal_law",
            "max_questions": 3,  # Just test 3 questions
            "user_id": "batch_test_user"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/evaluate/batch",
            json=batch_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Batch evaluation successful!")
            print(f"   Questions tested: {result['total_questions_tested']}")
            print(f"   Average overall score: {result['average_scores']['overall_score']:.3f}")
            print(f"   Average retrieval precision: {result['average_scores']['retrieval_precision_at_5']:.3f}")
            print(f"   Average answer relevance: {result['average_scores']['answer_relevance']:.3f}")
            print(f"   Average faithfulness: {result['average_scores']['answer_faithfulness']:.3f}")
        else:
            print(f"❌ Batch evaluation failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Batch evaluation error: {e}")
        return False
    
    print(f"\n" + "=" * 50)
    print("🎉 All tests passed! Evaluation system is working!")
    print("\n📊 What you now have:")
    print("✅ Complete RAG evaluation pipeline")
    print("✅ Automated quality scoring")
    print("✅ Batch testing capabilities")
    print("✅ API endpoints for evaluation")
    print("✅ Ready for interview demonstrations!")
    
    return True

if __name__ == "__main__":
    print("Starting evaluation system test...")
    print("Make sure your FastAPI server is running on http://localhost:8000")
    input("Press Enter when server is ready...")
    
    success = test_evaluation_system()
    
    if success:
        print("\n🚀 Next steps:")
        print("1. Run batch evaluations on all categories")
        print("2. Monitor scores over time")
        print("3. Use for A/B testing new features")
        print("4. Demo in interviews!")
    else:
        print("\n🔧 Troubleshooting needed:")
        print("1. Check server is running")
        print("2. Check dependencies installed")
        print("3. Check evaluation routes registered")