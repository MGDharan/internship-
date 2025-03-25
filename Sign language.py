import cv2
import mediapipe as mp
import numpy as np
import os
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split

# Initialize MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.8, min_tracking_confidence=0.8)

# File paths
DATASET_DIR = "asl_images"
MODEL_FILE = "asl_cnn_model.h5"
IMG_SIZE = 64
BATCH_SIZE = 32
EPOCHS = 10

# ASL Labels (A-Z)
labels = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
label_map = {label: i for i, label in enumerate(labels)}

# ------------------------- Step 1: Data Collection -------------------------
def collect_data():
    print("Press 's' to start collecting data. Show each letter when prompted.")
    os.makedirs(DATASET_DIR, exist_ok=True)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Unable to access the camera.")
        return
    
    collected = False
    current_label = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            continue
        
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        letter = labels[current_label]
        cv2.putText(frame, f"Show: {letter}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        if results.multi_hand_landmarks and collected:
            letter_dir = os.path.join(DATASET_DIR, letter)
            os.makedirs(letter_dir, exist_ok=True)
            img_path = os.path.join(letter_dir, f"{len(os.listdir(letter_dir))}.jpg")
            cv2.imwrite(img_path, frame)
            
        cv2.imshow("Collect Data", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            collected = True
        elif key == ord('n'):
            current_label = (current_label + 1) % len(labels)
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("Data collection complete.")

# ------------------------- Step 2: Train the CNN Model -------------------------
def load_data():
    images, labels_list = [], []
    
    for label in os.listdir(DATASET_DIR):
        letter_dir = os.path.join(DATASET_DIR, label)
        for img_file in os.listdir(letter_dir):
            img_path = os.path.join(letter_dir, img_file)
            img = cv2.imread(img_path)
            img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
            images.append(img)
            labels_list.append(label_map[label])
    
    images = np.array(images) / 255.0
    labels_list = np.array(labels_list)
    return train_test_split(images, labels_list, test_size=0.2, random_state=42)

def train_model():
    if not os.path.exists(DATASET_DIR):
        print("No dataset found. Run data collection first.")
        return
    
    X_train, X_test, y_train, y_test = load_data()
    
    model = keras.Sequential([
        layers.Conv2D(32, (3,3), activation='relu', input_shape=(IMG_SIZE, IMG_SIZE, 3)),
        layers.MaxPooling2D(2,2),
        layers.Conv2D(64, (3,3), activation='relu'),
        layers.MaxPooling2D(2,2),
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.Dense(len(labels), activation='softmax')
    ])
    
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE, validation_data=(X_test, y_test))
    model.save(MODEL_FILE)
    print("Model trained and saved!")

# ------------------------- Step 3: ASL Real-Time Recognition -------------------------
def recognize_asl():
    if not os.path.exists(MODEL_FILE):
        print("No trained model found. Train the model first.")
        return
    
    model = keras.models.load_model(MODEL_FILE)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Unable to access the camera.")
        return
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            continue
        
        frame = cv2.flip(frame, 1)
        img = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
        img = np.expand_dims(img, axis=0) / 255.0
        
        prediction = model.predict(img)
        predicted_label = labels[np.argmax(prediction)]
        
        cv2.putText(frame, f"Prediction: {predicted_label}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("ASL Recognition", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

# ------------------------- Main Execution -------------------------
if __name__ == "__main__":
    print("Choose an option:")
    print("1 - Collect ASL Sign Data")
    print("2 - Train CNN Model")
    print("3 - Recognize ASL in Real-Time")
    
    choice = input("Enter your choice (1/2/3): ")
    
    if choice == "1":
        collect_data()
    elif choice == "2":
        train_model()
    elif choice == "3":
        recognize_asl()
    else:
        print("Invalid choice!")
