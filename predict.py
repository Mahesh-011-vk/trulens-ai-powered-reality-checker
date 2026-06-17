import argparse
import joblib
import os

def load_model(model_path='models/model.pkl'):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}. Please run train.py first.")
    return joblib.load(model_path)

def predict(text, model):
    proba = model.predict_proba([text])[0]
    classes = model.classes_
    prediction = model.predict([text])[0]
    
    print(f"\nText: \"{text}\"")
    print("-" * 40)
    print(f"Prediction: {prediction}")
    print("Confidence Scores:")
    for cls, prob in zip(classes, proba):
        print(f"  {cls}: {prob:.4f}")
        
    return prediction

def main():
    parser = argparse.ArgumentParser(description="Predict if a text is REAL or FAKE news.")
    parser.add_argument("text", type=str, help="The news text to classify.")
    parser.add_argument("--model", type=str, default="models/model.pkl", help="Path to the trained model.")
    args = parser.parse_args()

    try:
        model = load_model(args.model)
        predict(args.text, model)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
