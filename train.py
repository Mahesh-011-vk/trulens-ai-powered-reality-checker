import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib

def main():
    # Ensure models directory exists
    os.makedirs('models', exist_ok=True)
    
    data_path = 'data/fake_or_real_news.csv'
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found.")
        return

    print("Loading data...")
    df = pd.read_csv(data_path)
    
    if 'text' not in df.columns or 'label' not in df.columns:
        print("Data must contain 'text' and 'label' columns.")
        return
        
    X = df['text']
    y = df['label']
    
    print(f"Loaded {len(df)} records.")
    print("Splitting data into training and validation sets...")
    
    if len(df) > 5:
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    else:
        X_train, X_val, y_train, y_val = X, X, y, y
        print("Warning: Dataset is too small, evaluating on training data.")
        
    print("Building and training the model...")
    # Pipeline: TF-IDF feature extraction -> Logistic Regression classifier
    model = make_pipeline(
        TfidfVectorizer(stop_words='english', max_df=0.7),
        LogisticRegression()
    )
    
    model.fit(X_train, y_train)
    
    print("Evaluating the model...")
    predictions = model.predict(X_val)
    print(f"Accuracy: {accuracy_score(y_val, predictions):.4f}")
    if len(set(y_val)) > 1:
        print("\nClassification Report:")
        print(classification_report(y_val, predictions, zero_division=0))
        
    # Save the model
    model_path = 'models/model.pkl'
    joblib.dump(model, model_path)
    print(f"Model successfully saved to {model_path}!")

if __name__ == '__main__':
    main()
