#importing all the required libraries
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import AveragePooling2D
from tensorflow.keras.layers import Dropout
from tensorflow.keras.layers import Flatten
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import Input
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.preprocessing.image import load_img
from tensorflow.keras.utils import to_categorical
from sklearn.preprocessing import LabelBinarizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from imutils import paths
import matplotlib.pyplot as matplt
import numpy as np
import os

# initialize the initial learning rate, number of epochs to train for,and batch size
learning_rate = 1e-4
EPOCHS = 10
Batch_size = 32

DIRECTORY = r"dataset"
CATEGORIES = ["with_mask", "without_mask"]

# grab the list of images in our dataset directory, then initialize the list of data (i.e., images) and class images
print("IMAGE LOADING")

data = []
labels = []
for category in CATEGORIES:
    path = os.path.join(DIRECTORY, category)
    for img in os.listdir(path):
    	img_path = os.path.join(path, img)
    	image = load_img(img_path, target_size=(224, 224))
    	image = img_to_array(image)
    	image = preprocess_input(image)

    	data.append(image)
    	labels.append(category)

lb = LabelBinarizer()
labels = lb.fit_transform(labels)
labels = to_categorical(labels)

data = np.array(data, dtype="float32")
labels = np.array(labels)

# distribution of data set int testing and training
(trainX, testX, trainY, testY) = train_test_split(data, labels,test_size=0.20, stratify=labels, random_state=42)

# construct the training image generator for data augmentation
aug = ImageDataGenerator(
	rotation_range=20,
	zoom_range=0.15,
	width_shift_range=0.2,
	height_shift_range=0.2,
	shear_range=0.15,
	horizontal_flip=True,
	fill_mode="nearest")

# loading of MobileNetV2 network
baseModel = MobileNetV2(weights="imagenet", include_top=False,input_tensor=Input(shape=(224, 224, 3)))

# construct the head of the model that will be placed on top of the base model
headModel = baseModel.output
headModel = AveragePooling2D(pool_size=(7, 7))(headModel)
headModel = Flatten(name="flatten")(headModel)
headModel = Dense(128, activation="relu")(headModel)
headModel = Dropout(0.5)(headModel)
headModel = Dense(2, activation="softmax")(headModel)
model = Model(inputs=baseModel.input, outputs=headModel)

# loop over all layers in the base model and freeze them so they will not be updated during the first training process
for layer in baseModel.layers:
	layer.trainable = False

# compile our model
print("Compiling")
opt = Adam(lr=learning_rate, decay=learning_rate / EPOCHS)
model.compile(loss="binary_crossentropy", optimizer=opt,metrics=["accuracy"])

# train the head of the network
print("Training the head")
H = model.fit(
	aug.flow(trainX, trainY, batch_size=Batch_size),
	steps_per_epoch=len(trainX) // Batch_size,
	validation_data=(testX, testY),
	validation_steps=len(testX) // Batch_size,
	epochs=EPOCHS)

# make predictions on the testing set
print("Evaluation of the model network")
predIdxs = model.predict(testX, batch_size=Batch_size)

# for each image in the testing set we need to find the index of the label with corresponding largest predicted probability
predIdxs = np.argmax(predIdxs, axis=1)
print(classification_report(testY.argmax(axis=1), predIdxs,target_names=lb.classes_))

# serialize the model to disk
print("[INFO] saving mask detector model...")
model.save("mask_detector.model", save_format="h5")

# plot the training loss and accuracy
N = EPOCHS
matplt.style.use("ggplot")
matplt.figure()
matplt.plot(np.arange(0, N), H.history["loss"], label="train_loss")
matplt.plot(np.arange(0, N), H.history["val_loss"], label="val_loss")
matplt.plot(np.arange(0, N), H.history["accuracy"], label="train_acc")
matplt.plot(np.arange(0, N), H.history["val_accuracy"], label="val_acc")
matplt.title("Training Loss and Accuracy")
matplt.xlabel("Epoch #")
matplt.ylabel("Loss/Accuracy")
matplt.legend(loc="lower left")
matplt.savefig("plot.png")