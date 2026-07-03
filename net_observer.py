import numpy as np
from sklearn.ensemble import IsolationForest


class NetworkObserver:
    def __init__(self):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42,
        )
        self.trained = False
        self.training_data = []

    def add_training_sample(self, cpu, memory, network):
        self.training_data.append([cpu, memory, network])
        if len(self.training_data) >= 50:
            self.model.fit(np.array(self.training_data))
            self.trained = True

    def detect(self, cpu, memory, network):
        if not self.trained:
            return False, "Model not trained yet"
        prediction = self.model.predict([[cpu, memory, network]])
        if prediction[0] == -1:
            return True, "Anomalous system behavior detected"
        return False, "Normal behavior"