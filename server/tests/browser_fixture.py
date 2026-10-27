"""Local browser-test server. Uses sample questions and never calls an AI API.

Run from server/: python -m uvicorn tests.browser_fixture:app --port 8000
Do not deploy this fixture; the real entry point is app.main:app.
"""
from app.main import app
from app.models import Question
from app.routers import questions


async def sample_questions(_source_text: str, num_questions: int = 5):
    samples = [
        Question(question="Where does photosynthesis take place?",
                 options=["Mitochondria", "Chloroplasts", "Nucleus", "Ribosomes"],
                 correct_index=1, explanation="Chloroplasts capture light energy to make sugars."),
        Question(question="Which gas do plants absorb during photosynthesis?",
                 options=["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"],
                 correct_index=2, explanation="Plants use carbon dioxide and water to make glucose."),
        Question(question="What is the main energy source for photosynthesis?",
                 options=["Sunlight", "Soil", "Wind", "Minerals"],
                 correct_index=0, explanation="Light energy powers photosynthesis."),
    ]
    return [samples[index % len(samples)] for index in range(num_questions)]


questions.generate_questions = sample_questions
