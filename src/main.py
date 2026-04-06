print(">>> main.py started")

from .game_controller import run

print(">>> imported run() successfully")

if __name__ == "__main__":
    print(">>> calling run()")
    run()
    print(">>> run() returned")
