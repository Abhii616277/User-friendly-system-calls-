import os, shutil
from PIL import Image

# <-- update these source paths if needed (these are the generated files I have)
src1 = r"/mnt/data/A_digital_screenshot_of_a_computer_file_explorer_w.png"
src2 = r"/mnt/data/A_digital_screenshot_displays_a_Windows_File_Explo.png"

# target folder (must be next to your script)
script_dir = os.path.dirname(os.path.abspath(__file__))
img_folder = os.path.join(script_dir, "img")

os.makedirs(img_folder, exist_ok=True)

# copy; use safe names 1.png and 2.png
dst1 = os.path.join(img_folder, "1.png")
dst2 = os.path.join(img_folder, "2.png")

try:
    shutil.copyfile(src1, dst1)
    shutil.copyfile(src2, dst2)
    print("Copied images to:", img_folder)
except Exception as e:
    print("Error copying files:", e)
    print("Make sure the source paths exist on your machine.")
    raise SystemExit(1)

# quick sanity: list folder contents
print("Files in img/:", os.listdir(img_folder))

# Optional quick test: open the images with PIL to ensure they're valid
for p in (dst1, dst2):
    try:
        im = Image.open(p)
        print(f"Image OK: {os.path.basename(p)} size={im.size}, mode={im.mode}")
        im.close()
    except Exception as e:
        print("Failed to open image:", p, e)

# If you want, run your viewer (uncomment one of these lines)
# os.system(f'py -3.10 Gui.py')    # runs Gui.py with py launcher (Python 3.10)
# os.system(f'py -3.10 project.py')# or runs project.py
