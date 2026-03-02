import os
import spacy
from spacy.training import Example
from spacy.util import minibatch
from typing import List, Dict
from src.utils.feedback_collector import get_feedback_collector


MODEL_PATH = "models/resume_model"
UPDATED_MODEL_PATH = "models/resume_model_updated"


def build_spacy_examples(training_data: List[Dict]):
    examples = []
    nlp = spacy.blank("en")

    for item in training_data:
        text = item["input"]
        corrected = item["output"]
        field = item["field"].upper()

        if not text or not corrected:
            continue

        start = text.find(corrected)
        if start == -1:
            continue

        end = start + len(corrected)

        doc = nlp.make_doc(text)
        example = Example.from_dict(
            doc,
            {"entities": [(start, end, field)]}
        )
        examples.append(example)

    return examples


def retrain_model():
    feedback_collector = get_feedback_collector()

    print("Exporting feedback data...")
    training_data = feedback_collector.export_training_data()

    if not training_data:
        print("No training data found.")
        return

    print(f"Found {len(training_data)} training samples")

    print("Loading existing model...")
    nlp = spacy.load(MODEL_PATH)

    ner = nlp.get_pipe("ner")

    for item in training_data:
        ner.add_label(item["field"].upper())

    examples = build_spacy_examples(training_data)

    print("Starting training...")
    optimizer = nlp.resume_training()

    for epoch in range(5):
        losses = {}
        batches = minibatch(examples, size=8)

        for batch in batches:
            nlp.update(batch, sgd=optimizer, losses=losses)

        print(f"Epoch {epoch+1} Loss: {losses}")

    print("Saving updated model...")
    nlp.to_disk(UPDATED_MODEL_PATH)

    print("Marking feedback as processed...")
    for filename in os.listdir(feedback_collector.storage_path):
        if filename.endswith(".json"):
            feedback_id = filename.replace(".json", "")
            feedback_collector.mark_as_processed(feedback_id)

    print("Retraining completed successfully.")
