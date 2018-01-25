import os
import threading
import numpy as np
from PIL import Image
import keras
from keras.preprocessing.image import ImageDataGenerator, Iterator, load_img, img_to_array


def get_all_images():
    return os.listdir('data/')


def get_images():
    data = {
        'firefox': [],
        'chrome': [],
    }

    for file_name in get_all_images():
        assert 'firefox.png' in file_name or 'chrome.png' in file_name

        browser = 'firefox' if 'firefox.png' in file_name else 'chrome'

        data[browser].append(file_name[:file_name.index('_' + browser + '.png')])

    return [image for image in data['firefox'] if image in set(data['chrome'])]


def prepare_images():
    try:
        os.mkdir('data_resized')
    except:
        pass

    for f in os.listdir('data/'):
        if os.path.exists(os.path.join('data_resized', f)):
            continue

        try:
            orig = Image.open(os.path.join('data', f))
            orig.load()
            channels = orig.split()
            if len(channels) == 4:
                img = Image.new('RGB', orig.size, (255, 255, 255))
                img.paste(orig, mask=channels[3])
            else:
                img = orig

            img = img.resize((192, 256), Image.LANCZOS)
            img.save(os.path.join('data_resized', f))
        except IOError as e:
            print(e)


images = {}
def load_image(fname):
    global images

    if fname in images:
        return images[fname]

    img = load_img(os.path.join('data_resized', fname), target_size=(32,24))
    x = img_to_array(img, data_format=keras.backend.image_data_format())

    images[fname] = x

    return x


def get_ImageDataGenerator(images, image_shape):
    data_gen = ImageDataGenerator(rescale=1./255)

    x = np.zeros((len(images),) + image_shape, dtype=keras.backend.floatx())

    for i, image in enumerate(images):
        x[i] = load_image(image)

    data_gen.fit(x)

    return data_gen


class CouplesIterator():
    def __init__(self, image_couples_generator, image_shape, image_data_generator, batch_size=32):
        self.image_couples_generator = image_couples_generator
        self.image_shape = image_shape
        self.image_data_generator = image_data_generator
        self.batch_size = batch_size
        self.lock = threading.Lock()

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def next(self):
        x_batch = [
            np.zeros((self.batch_size,) + self.image_shape, dtype=keras.backend.floatx()),
            np.zeros((self.batch_size,) + self.image_shape, dtype=keras.backend.floatx()),
        ]
        image_couples = [None] * self.batch_size
        y_batch = np.zeros(self.batch_size)

        with self.lock:
            for i in range(self.batch_size):
                image_couple, label = next(self.image_couples_generator)
                image_couples[i] = image_couple
                y_batch[i] = label

        for i, (i1, i2) in enumerate(image_couples):
            x1 = load_image(i1)
            x1 = self.image_data_generator.random_transform(x1.astype(keras.backend.floatx()))
            x1 = self.image_data_generator.standardize(x1)
            x2 = load_image(i2)
            x2 = self.image_data_generator.random_transform(x2.astype(keras.backend.floatx()))
            x2 = self.image_data_generator.standardize(x2)
            x_batch[0][i] = x1
            x_batch[1][i] = x2

        return x_batch, y_batch