# Dungeon PCG Project

This project is a 2D dungeon crawler that uses procedural content generation (PCG) to automatically create dungeon maps. Instead of manually designing levels, the system generates them using a cellular automata approach and then validates them to ensure they are playable.

The aim of the project is to produce varied and playable maps while maintaining key requirements such as connectivity and solvability. The generated maps are integrated into a fully playable game built using Python and Pygame.

---

## Features

- Procedural dungeon generation using cellular automata  
- Playability validation using breadth-first search (BFS)  
- Grid-based map representation  
- Turn-based combat system  
- Enemies, traps, and health pickups  
- Fog-of-war system with adjustable difficulty  
- Fully playable game environment  

---

## How to Run

1. Clone the repository:
```
git clone https://github.com/Rhys11Evans/dungeon-pcg-project
```

2. Navigate to the project folder:
```
cd dungeon-pcg-project
```

3. Create a virtual environment:
```
py -3.12 -m venv .venv
```

4. Activate the virtual environment:
```
.venv\Scripts\activate
```

5. Install dependencies:
```
pip install pygame
```

6. Run the game:
```
py -m src.main
```

---

## Controls

- **WASD / Arrow Keys** – Move  
- **SPACE + Mouse Direction** – Attack  
- **R** – Restart game  

---

## Project Structure

```
src/
  main.py
  game_controller.py
  dungeon/
    generator_ca.py
    grid.py
    evaluator.py
  render/
    renderer_pygame.py

assets/
  tiles/
  player/
  enemies/
  traps/
```

---

## Report

This project was developed as part of the UWE Digital Systems Project module.  
The full report explains the design, implementation, and evaluation of the procedural generation system.

---

## Acknowledgements

- Kenney (2023) asset pack used for game visuals  
- Built using Python and Pygame  
