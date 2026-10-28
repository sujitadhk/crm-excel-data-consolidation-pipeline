import sys
sys.path.insert(0, "src")
from generate_sample_data import main as generate
from pipeline import run

if __name__ == "__main__":
    generate()
    stats, results = run()
    print(stats)
    print(results)
