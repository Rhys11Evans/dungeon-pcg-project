"""
Configuration values for the dungeon generation system.
Keeping settings in one place makes tuning and testing easier.
"""

GRID_W = 60
GRID_H = 40

CELL_SIZE = 16

# Cellular automata parameters
FILL_PROB = 0.45
STEPS = 5
BIRTH_LIMIT = 4
DEATH_LIMIT = 3

# Evaluation / regeneration
MAX_RETRIES = 30
