"""Create a deterministic synthetic Git repository; never executes downloaded code."""
import subprocess
from pathlib import Path

def create(root):
    root = Path(root).resolve()
    if root.exists():
        raise ValueError('Choose a new directory; refusing to overwrite an existing repository')
    root.mkdir(parents=True)
    def git(*args):
        subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, timeout=15)
    git('init')
    git('config', 'user.name', 'Synthetic Demo Author')
    git('config', 'user.email', 'demo@example.invalid')
    (root / 'README.md').write_text('# Synthetic SkillProof demo\nPython order totals with validation and unit tests.\nThis repository demonstrates code evidence, not candidate identity.\n', encoding='utf-8')
    git('add', '.')
    git('commit', '-m', 'Document synthetic order processing project')
    (root / 'orders.py').write_text('''def total(items, discount=0):
    if not 0 <= discount <= 1:
        raise ValueError("discount must be between zero and one")
    amount = 0
    for price, quantity in items:
        if price < 0 or quantity < 0:
            raise ValueError("negative item")
        amount += price * quantity
    return round(amount * (1 - discount), 2)

def legacy_total(items):
    result = 0
    for price, quantity in items:
        result += price * quantity
    return result

def duplicate_total(items):
    result = 0
    for price, quantity in items:
        result += price * quantity
    return result

def suspicious_parse(value):
    try:
        return float(value)
    except:
        return 0
''', encoding='utf-8')
    git('add', '.')
    git('commit', '-m', 'Implement validated totals and legacy helpers')
    (root / 'test_orders.py').write_text('''import pytest
from orders import total

def test_total():
    assert total([(10, 2)], .1) == 18

def test_invalid():
    with pytest.raises(ValueError):
        total([(-1, 2)])

def test_empty():
    assert total([]) == 0
''', encoding='utf-8')
    git('add', '.')
    git('commit', '-m', 'Test totals, invalid inputs and empty orders')
    return root

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='?', default='../demo_repository')
    print(create(parser.parse_args().path))
