# -*- coding: utf-8 -*-
"""Monetifyw/oGradio.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1N9XB19v_3amQCgR7n1HcujO-ydI_fn38
"""

import torch
import time  # track time
import torch.nn as nn
import torch.optim as optim
#import gradio as gr
from PIL import Image  # This will be used to load the image (or images)
import torchvision.transforms as transforms  # Transforms to convert image to a tensor
import torchvision.models as models  # Loads vgg19 (which is also manually installed in computer, code in the path*)
from torchvision.models import VGG19_Weights  # Rids outdated pretrained parameter
from torchvision.utils import save_image  # Store the generated image at the end

# Use the updated weights parameter
model = models.vgg19(weights=VGG19_Weights.IMAGENET1K_V1).features

# print(model)  # We take every conv layer after each Maxpool [0, 5, 10, 19, 28]
# Any layer after [28] we won't need in our loss function

# Create a class VGG:
class VGG(nn.Module):
    def __init__(self):
        super(VGG, self).__init__()

        self.chosen_features = ['0', '5', '10', '19', '28']  # Conv layers we are taking
        self.model = models.vgg19(weights=VGG19_Weights.IMAGENET1K_V1).features[:29]
        # Go up to 29, where we have inclusive of 28

    def forward(self, x):  # We're going to store features in an empty array/list
        features = []  # These features will be the relevant features

        for layer_num, layer in enumerate(self.model):
            x = layer(x)  # We can send in x through the layer and our output will be called x

            if str(layer_num) in self.chosen_features:  # If string of layer_num is in self.chosen_features, then store it
                features.append(x)

        return features  # Lastly, return features

# Now create a function that can load an image, PIL library used here
def load_image(image_name):
    image = Image.open(image_name)
    image = loader(image).unsqueeze(0)  # Unsqueeze 0 to add another dimension for the batch size, which will be 1
    return image.to(device)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
image_size = 256  # Specify image size, we have cpu so let's adjust to a lower size if we don't want it to take long

loader = transforms.Compose([
    transforms.Resize((image_size, image_size)), # All images must be of the SAME SIZE! or we won't be able to subtract them when computing loss
    transforms.ToTensor(),
    #transforms.Normalize(mean=[], std =[] # Can find mean and std and put them here to uncomment, can improve result a little
])

# Grab original and style image on device
original_img = load_image('/content/city.jpg')
style_img = load_image('/content/monet123.jpg')
model = VGG().to(device).eval()  # .eval() to freeze the weights
generated = original_img.clone().requires_grad_(True)  # Essential to freeze the network, so the only thing that changes is the generated image

# Hyperparameters:
total_steps = 1001
learning_rate = 0.001
# How much style we want in the image: (still under hyperparameters):
alpha = 1  # Different numbers in the paper
beta = 0.01  # Different numbers in the paper
optimizer = optim.Adam([generated], lr=learning_rate)  # Normally would do model.parameters, but we use generated to optimize the image
# then send in the learning rate

#Time:
start_time = time.time()

for step in range(total_steps):  # How many times the image will be modified
    generated_features = model(generated)  # We need to send in each of the 3 images through the VGG network
    original_features = model(original_img)
    style_features = model(style_img)

    style_loss = original_loss = 0
    # now we'll iterate through all the features for the chosen layers:
    for gen_feature, orig_feature, style_feature in zip(generated_features, original_features, style_features):  # Everything in the 5 conv layers
        # We're just taking the first conv 1-1 for gen, orig, and style, then iterate through all 5 of them eventually:
        batch_size, channel, height, width = gen_feature.shape  # remember our batch size is only one!
        original_loss += torch.mean((gen_feature - orig_feature) ** 2)  # From equation

        # Compute the Gram Matrix
        # Here, we've multiplied every pixel value from each channel with every other channel for the generated features
        # this is then later subtracted with style gram matrix
        G = gen_feature.view(channel, height * width).mm(  # Matrix multiplication
            gen_feature.view(channel, height * width).t()  # Tranpose
        )

        # Calculate gram matrix for style
        A = style_feature.view(channel, height * width).mm(
            style_feature.view(channel, height * width).t()
        )

        # Now that we have both matrices, we calculate style loss
        style_loss += torch.mean((G - A) ** 2)

    # After, calculate total loss
    total_loss = alpha * original_loss + beta * style_loss
    optimizer.zero_grad()
    total_loss.backward()
    optimizer.step()

    if step % 100 == 0:  # Log more frequently for testing
        print(f'Step [{step}/{total_steps}], Total Loss: {total_loss.item()}')
        save_image(generated, f'/content/generated/generated_{step}.png')

end_time = time.time()
elapsed_time = end_time - start_time
print(f'Total time for {total_steps} steps: {elapsed_time} seconds')