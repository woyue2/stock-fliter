import argparse
import sys
import os
from datetime import datetime

# Add project root to path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from check_smile_magic.pipeline import SmileMagicPipeline

def main():
    parser = argparse.ArgumentParser(description='Smile Number Strategy (Magic Number + Smile Curve)')
    parser.add_argument('--code', type=str, help='Stock code (e.g., 600121)')
    parser.add_argument('--date', type=str, help='Analysis date (YYYY-MM-DD)')
    parser.add_argument('--test', action='store_true', help='Test mode (analyze a few random stocks)')
    
    args = parser.parse_args()
    
    pipeline = SmileMagicPipeline()
    
    codes = None
    if args.code:
        codes = [args.code]
    elif args.test:
        import random
        all_codes = list(pipeline.stock_info.keys())
        codes = random.sample(all_codes, min(10, len(all_codes)))
        print(f"Test mode: Analyzing {len(codes)} random stocks...")
        
    date = args.date if args.date else datetime.now().strftime('%Y-%m-%d')
    
    print(f"Running Smile Number Strategy for {date}...")
    results = pipeline.run(code_list=codes, target_date=date)
    
    if results.empty:
        print("No matches found.")
    else:
        print("\nMatches Found:")
        print(results.to_string(index=False))
        
        # Save to output
        out_dir = os.path.join(os.path.dirname(__file__), 'output', datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(out_dir, exist_ok=True)
        filename = f"matches_{datetime.now().strftime('%H%M%S')}.csv"
        results.to_csv(os.path.join(out_dir, filename), index=False, encoding='utf-8-sig')
        print(f"\nResults saved to: {os.path.join(out_dir, filename)}")

if __name__ == '__main__':
    main()
