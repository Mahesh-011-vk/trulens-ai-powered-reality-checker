import torch
import torch.nn as nn
import torch.nn.functional as F
import re
import json
import os

class CNNClassifier(nn.Module):
    def __init__(self, vocab_size, embedding_dim=50, num_filters=64, kernel_size=3, num_classes=2):
        super(CNNClassifier, self).__init__()
        # Padding index is 0 (<pad>)
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.conv = nn.Conv1d(in_channels=embedding_dim, out_channels=num_filters, kernel_size=kernel_size, padding=1)
        self.dropout = nn.Dropout(0.5)
        self.fc = nn.Linear(num_filters, num_classes)

    def forward(self, x):
        # x: [batch_size, seq_len]
        embedded = self.embedding(x) # [batch_size, seq_len, embedding_dim]
        embedded = embedded.transpose(1, 2) # [batch_size, embedding_dim, seq_len] (expected format for Conv1d)
        
        conved = F.relu(self.conv(embedded)) # [batch_size, num_filters, seq_len]
        
        # Max pool over the entire sequence length
        pooled = F.adaptive_max_pool1d(conved, 1).squeeze(2) # [batch_size, num_filters]
        
        dropped = self.dropout(pooled)
        logits = self.fc(dropped) # [batch_size, num_classes]
        return logits

class CNNTextProcessor:
    def __init__(self, vocab_path=None, max_len=200):
        self.max_len = max_len
        self.word2idx = {"<pad>": 0, "<unk>": 1}
        self.idx2word = {0: "<pad>", 1: "<unk>"}
        
        if vocab_path and os.path.exists(vocab_path):
            self.load_vocab(vocab_path)

    def clean_text(self, text):
        if not isinstance(text, str):
            text = str(text)
        text = text.lower()
        # Remove punctuation and special characters
        text = re.sub(r'[^\w\s]', '', text)
        return text

    def tokenize(self, text):
        cleaned = self.clean_text(text)
        return cleaned.split()

    def build_vocab(self, texts, max_vocab_size=10000):
        word_counts = {}
        for text in texts:
            tokens = self.tokenize(text)
            for token in tokens:
                word_counts[token] = word_counts.get(token, 0) + 1
        
        # Sort words by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        # Keep top max_vocab_size words
        for word, _ in sorted_words[:max_vocab_size - 2]:
            if word not in self.word2idx:
                idx = len(self.word2idx)
                self.word2idx[word] = idx
                self.idx2word[idx] = word

    def save_vocab(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.word2idx, f, ensure_ascii=False, indent=2)

    def load_vocab(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            self.word2idx = json.load(f)
        self.idx2word = {int(idx): word for word, idx in self.word2idx.items()}

    def text_to_sequence(self, text):
        tokens = self.tokenize(text)
        seq = [self.word2idx.get(token, self.word2idx["<unk>"]) for token in tokens]
        
        # Padding or truncation
        if len(seq) < self.max_len:
            seq = seq + [self.word2idx["<pad>"]] * (self.max_len - len(seq))
        else:
            seq = seq[:self.max_len]
        return seq

    @property
    def vocab_size(self):
        return len(self.word2idx)
