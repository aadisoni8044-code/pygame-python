import pygame
import sys

pygame.init()

# Screen settings
WIDTH, HEIGHT = 400, 550
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Calculator")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (150, 150, 150)

# Fonts
font = pygame.font.SysFont(None, 48)
small_font = pygame.font.SysFont(None, 40)

# Calculator variables
current_input = ""
result = ""

# Button layout
buttons = [
    ['7', '8', '9', '/'],
    ['4', '5', '6', '*'],
    ['1', '2', '3', '-'],
    ['0', 'C', '=', '+']
]

button_rects = []

# Create button rectangles
bx, by = 20, 150
bw, bh = 80, 80
for row in buttons:
    rect_row = []
    for _ in row:
        rect_row.append(pygame.Rect(bx, by, bw, bh))
        bx += bw + 20
    button_rects.append(rect_row)
    bx = 20
    by += bh + 20


def draw():
    screen.fill(WHITE)

    # Display box
    display_rect = pygame.Rect(20, 20, 360, 100)
    pygame.draw.rect(screen, GRAY, display_rect, border_radius=10)

    # Text in the display
    display_text = font.render(current_input if current_input else result, True, BLACK)
    screen.blit(display_text, (30, 50))

    # Draw buttons
    for i, row in enumerate(button_rects):
        for j, rect in enumerate(row):
            pygame.draw.rect(screen, DARK_GRAY, rect, border_radius=10)
            label = small_font.render(buttons[i][j], True, BLACK)
            screen.blit(label, (rect.x + 30, rect.y + 25))

    pygame.display.update()


def handle_click(x, y):
    global current_input, result

    for i, row in enumerate(button_rects):
        for j, rect in enumerate(row):
            if rect.collidepoint(x, y):
                value = buttons[i][j]
                if value == 'C':
                    current_input = ""
                    result = ""
                elif value == '=':
                    try:
                        result = str(eval(current_input))
                        current_input = ""
                    except:
                        result = "Error"
                        current_input = ""
                else:
                    current_input += value


# Main loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            handle_click(*event.pos)

    draw()

pygame.quit()
sys.exit()

