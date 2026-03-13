from lightweight_charts import Chart
import inspect

def main():
    chart = Chart()
    print("Chart Methods:")
    for name, member in inspect.getmembers(chart, predicate=inspect.ismethod):
        if not name.startswith('_'):
            print(f" - {name}")
            
if __name__ == "__main__":
    main()
