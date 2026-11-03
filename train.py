# train.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pickle

# Load data
df = pd.read_csv('dataset.csv')
print("Data Loaded:", df.shape)

X = df[['prev_month_att','assignments_submitted','avg_class_hours','late_count','internal_marks']]
y = df['final_risk']

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Check Accuracy
pred = model.predict(X_test)
acc = accuracy_score(y_test, pred)
print(f"Model Accuracy: {acc*100:.2f}%")

# Save model
with open('AttendAI_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Model saved as AttendAI_model.pkl")