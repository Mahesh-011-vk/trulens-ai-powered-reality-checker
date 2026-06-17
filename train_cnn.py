import os
import json
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from cnn_model import CNNClassifier, CNNTextProcessor

# Define custom Dataset class
class NewsDataset(Dataset):
    def __init__(self, sequences, labels):
        self.sequences = torch.tensor(sequences, dtype=torch.long)
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]

def train_model():
    # Ensure models directory exists
    os.makedirs('models', exist_ok=True)
    
    data_path = 'data/fake_or_real_news.csv'
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found. Please download it or check file path.")
        return

    print("Loading dataset...")
    df = pd.read_csv(data_path)
    
    # GeorgeMcIntire dataset contains columns: 'title', 'text', 'label'
    if 'text' not in df.columns or 'label' not in df.columns:
        print("Dataset must contain 'text' and 'label' columns.")
        return
    
    # Remove empty texts
    df = df.dropna(subset=['text', 'label'])
    
    # Map labels: FAKE -> 0, REAL -> 1
    # Check what labels exist in the dataset
    print(f"Unique labels in dataset: {df['label'].unique()}")
    label_map = {"FAKE": 0, "REAL": 1}
    df['label_idx'] = df['label'].map(label_map)
    df = df.dropna(subset=['label_idx'])
    
    X = df['text'].tolist()
    y = df['label_idx'].astype(int).tolist()
    
    print(f"Loaded {len(X)} records.")
    
    # Step 1: Preprocessing & Vocabulary
    print("Building vocabulary...")
    processor = CNNTextProcessor(max_len=200)
    processor.build_vocab(X, max_vocab_size=10000)
    vocab_path = 'models/cnn_vocab.json'
    processor.save_vocab(vocab_path)
    print(f"Vocabulary saved to {vocab_path}. Size: {processor.vocab_size}")
    
    # Step 2: Convert texts to sequences
    print("Converting texts to sequences...")
    sequences = [processor.text_to_sequence(text) for text in X]
    
    # Step 3: Train-Val Split
    X_train, X_val, y_train, y_val = train_test_split(sequences, y, test_size=0.2, random_state=42)
    
    train_dataset = NewsDataset(X_train, y_train)
    val_dataset = NewsDataset(X_val, y_val)
    
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)
    
    # Step 4: Model setup
    device = torch.device('cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu'))
    print(f"Training on device: {device}")
    
    model = CNNClassifier(
        vocab_size=processor.vocab_size,
        embedding_dim=50,
        num_filters=64,
        kernel_size=3,
        num_classes=2
    ).to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    # Step 5: Training loop
    epochs = 5
    print("Starting training...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        correct_train = 0
        total_train = 0
        
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item() * batch_x.size(0)
            _, predicted = torch.max(outputs, 1)
            correct_train += (predicted == batch_y).sum().item()
            total_train += batch_y.size(0)
            
        train_loss = total_loss / total_train
        train_acc = correct_train / total_train
        
        # Validation
        model.eval()
        correct_val = 0
        total_val = 0
        val_loss = 0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item() * batch_x.size(0)
                _, predicted = torch.max(outputs, 1)
                correct_val += (predicted == batch_y).sum().item()
                total_val += batch_y.size(0)
                
        val_loss = val_loss / total_val
        val_acc = correct_val / total_val
        
        print(f"Epoch {epoch+1}/{epochs} | Train Loss: {train_loss:.4f} | Train Acc: {train_acc*100:.2f}% | Val Loss: {val_loss:.4f} | Val Acc: {val_acc*100:.2f}%")
        
    # Step 6: Save model
    model_path = 'models/cnn_model.pth'
    torch.save(model.state_dict(), model_path)
    print(f"CNN Model successfully saved to {model_path}!")

if __name__ == '__main__':
    train_model()
