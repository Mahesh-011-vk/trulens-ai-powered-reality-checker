import urllib.request
import urllib.error
import argparse
import sys
import json

API_URL = "http://127.0.0.1:8000/analyze"

def analyze_text(text):
    print(f"Analyzing text: \"{text}\"...\n")
    try:
        data = json.dumps({"text": text}).encode('utf-8')
        req = urllib.request.Request(
            API_URL, 
            data=data, 
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                print("=" * 40)
                
                # Simple color formatting for the prediction
                pred = result['prediction']
                if pred == "FAKE":
                    pred_str = f"\033[91m\033[1m{pred}\033[0m" # Red
                else:
                    pred_str = f"\033[92m\033[1m{pred}\033[0m" # Green
                    
                print(f"Prediction: {pred_str}")
                print("=" * 40)
                print("Confidence Scores:")
                for cls, conf in result['confidence'].items():
                    print(f" - {cls}: {conf:.4f}")
            else:
                print(f"Error: API returned status code {response.status}")
                print(response.read().decode('utf-8'))
                
    except urllib.error.URLError as e:
        print(f"\033[91mError: Failed to connect to API at {API_URL}.\033[0m")
        print(f"Details: {e.reason}")
        print("Please ensure the FastAPI server is running. You can start it via:")
        print("    source venv/bin/activate")
        print("    uvicorn app:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Terminal client for Fake News API.")
    parser.add_argument("text", type=str, help="The news text to classify.")
    args = parser.parse_args()

    analyze_text(args.text)

if __name__ == "__main__":
    main()
