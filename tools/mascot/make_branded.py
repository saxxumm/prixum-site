"""The user's skin with light Prixum details: odd eyes, a brand pink bow, a crystal hairpin, a crystal on the back,
a garter ribbon on one leg and pink inside the ears. The character itself stays as it was."""
import sys
from PIL import Image

im = Image.open(sys.argv[1]).convert("RGBA")
hx = lambda h: (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255)
PINK, PINK_LIGHT, PINK_DEEP, PINK_DARK = hx("#ff5fa2"), hx("#ff8cc3"), hx("#d94a93"), hx("#a73574")

def put(x, y, color):
    im.putpixel((x, y), color if isinstance(color, tuple) else hx(color))

# 1. odd eyes: the left eye (player's left, x 14 on the face) turns violet, the right one stays pink
put(14, 9, "#b47af2")
put(14, 10, "#8a52d6")

# 2. the bow on the chest in the brand pink: the knot darker, the tails a step deeper
for x in (22, 25):
    put(x, 22, PINK)
for x in (23, 24):
    put(x, 22, PINK_DEEP)
for y in (23, 24):
    put(22, y, PINK_LIGHT if y == 23 else PINK)
    put(25, y, PINK_LIGHT if y == 23 else PINK)
for y in (38, 39):  # the tails that stick out on the overlay
    put(22, y, PINK if y == 38 else PINK_DEEP)
    put(25, y, PINK if y == 38 else PINK_DEEP)

# 3. a crystal hairpin on the right side of the head (hat layer), with a sparkle
for (x, y), c in {(4, 2): "#ffcce3", (5, 2): "#ff7cb5", (4, 3): "#ff4f9a", (5, 3): "#d94a93", (4, 4): "#a73574", (5, 1): "#ffffff"}.items():
    put(32 + x, 8 + y, c)

# 4. the Prixum crystal on the back of the dress, between the shoulders
for (x, y), c in {(3, 3): "#ffcce3", (4, 3): "#ff7cb5", (3, 4): "#ff4f9a", (4, 4): "#d94a93", (3, 5): "#a73574", (4, 5): "#8c3563"}.items():
    put(32 + x, 20 + y, c)

# 5. a garter ribbon around the left leg only, with a small bow in front
for face_x in (16, 20, 24, 28):  # right side, front, left side, back of the left leg
    for i in range(4):
        put(face_x + i, 57, PINK)
put(22, 57, "#ffd3e7")
put(21, 56, PINK_LIGHT)
put(23, 56, PINK_LIGHT)

# 6. pink inside the cat ears
put(41, 1, "#f4a6b9")
put(46, 1, "#f4a6b9")

im.save(sys.argv[2])
print("saved", sys.argv[2])
