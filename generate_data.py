import pandas as pd
import numpy as np
np.random.seed(42)
data = {
    'prev_month_att': np.random.randint(40, 99, 500),
    'assignments_submitted': np.random.randint(0, 11, 500),
    'avg_class_hours': np.round(np.random.uniform(2, 8, 500),1),
    'late_count': np.random.randint(0, 16, 500),
    'internal_marks': np.random.randint(20, 96, 500),
}
df = pd.DataFrame(data)
df['final_risk'] = ((df['prev_month_att'] < 75) & (df['assignments_submitted'] < 5)).astype(int)
df.to_csv('dataset.csv', index=False)
print("dataset.csv created")