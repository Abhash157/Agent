from PIL import Image
import pytesseract

img = Image.open("ocr.png")  # Make sure this image has some text
text = pytesseract.image_to_string(img)

print("Detected Text:\n", text)
