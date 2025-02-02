import keras
import numpy as np
import tensorflow as tf
import re
from src.components.model import get_cnn_model, TransformerEncoderBlock, TransformerDecoderBlock, ImageCaptioningModel, image_augmentation, LRSchedule

SEQ_LENGTH = 25
VOCAB_SIZE = 10000
IMAGE_SIZE = (299, 299)

print("loading_model...")
loaded_model = keras.saving.load_model(
    "./artifacts/caption_model.keras", compile=True)
print("model loaded...")

vocab = np.load("./artifacts/vocabulary.npy")
print("vocab loaded...")
data_txt = np.load("./artifacts/data_txt.npy").tolist()
print("vectorization data loaded...")

index_lookup = dict(zip(range(len(vocab)), vocab))
print("index lookup loaded...")
max_decoded_sentence_length = SEQ_LENGTH - 1
strip_chars = "!\"#$%&'()*+,-./:;=?@[\]^_`{|}~"


def custom_standardization(input_string):
    lowercase = tf.strings.lower(input_string)
    return tf.strings.regex_replace(lowercase, f'{re.escape(strip_chars)}', '')


vectorization = keras.layers.TextVectorization(
    max_tokens=VOCAB_SIZE,
    output_mode="int",
    output_sequence_length=SEQ_LENGTH,
    standardize=custom_standardization,
)

vectorization.adapt(data_txt)
print("vectorization adapted...")


def decode_and_resize(image):
    if isinstance(image, str):
        img = tf.io.read_file(image)
        img = tf.image.decode_jpeg(img, channels=3)
    elif isinstance(image, np.ndarray):
        img = tf.constant(image)
    img = tf.image.resize(img, IMAGE_SIZE)
    img = tf.image.convert_image_dtype(img, tf.float32)
    return img


def generate_caption(image):
    
    sample_img = decode_and_resize(image)

    # Pass the image to the CNN
    img = tf.expand_dims(sample_img, 0)
    img = loaded_model.cnn_model(img)

    # Pass the image features to the Transformer encoder
    encoded_img = loaded_model.encoder(img, training=False)

    # Generate the caption using the Transformer decoder
    decoded_caption = "<start> "
    for i in range(max_decoded_sentence_length):
        tokenized_caption = vectorization([decoded_caption])
        mask = tf.math.not_equal(tokenized_caption, 0)
        predictions = loaded_model.decoder(
            tokenized_caption, encoded_img, training=False, mask=mask
        )
        sampled_token_index = np.argmax(predictions[0, i, :])
        sampled_token = index_lookup[sampled_token_index]
        if sampled_token == "<end>":
            break
        decoded_caption += " " + sampled_token

    decoded_caption = decoded_caption.replace("<start> ", "")
    decoded_caption = decoded_caption.replace(" <end>", "").strip()
    return decoded_caption
