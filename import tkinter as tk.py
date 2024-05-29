import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions

# Load MobileNet model
model = MobileNetV2(weights='imagenet')

def load_image():
    file_path = filedialog.askopenfilename()
    if file_path:
        img = Image.open(file_path)
        img = img.resize((224, 224))  # Resize for MobileNet
        img_array = np.array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)
        
        preds = model.predict(img_array)
        results = decode_predictions(preds, top=3)[0]
        
        result_text = "\n".join([f"{res[1]}: {res[2]*100:.2f}%" for res in results])
        result_label.config(text=result_text)
        
        img_tk = ImageTk.PhotoImage(img)
        image_label.config(image=img_tk)
        image_label.image = img_tk

# Create GUI
root = tk.Tk()
root.title("MobileNet Image Classifier")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

load_button = tk.Button(frame, text="Load Image", command=load_image)
load_button.pack()

image_label = tk.Label(frame)
image_label.pack()

result_label = tk.Label(frame, text="", justify=tk.LEFT)
result_label.pack()

root.mainloop()
