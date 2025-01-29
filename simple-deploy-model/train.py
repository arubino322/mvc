import pandas as pd
import pickle
from prophet import Prophet

df = pd.read_csv('data.csv')

# fit model
m = Prophet()
m.fit(df)
print("Training complete!")

with open('model.pickle', 'wb') as f:
    pickle.dump(m, f)
