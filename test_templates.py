import os
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

def test_templates():
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    
    errors = False
    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                # Get relative path for jinja loader
                rel_path = os.path.relpath(os.path.join(root, file), template_dir)
                # Ensure forward slashes for jinja
                rel_path = rel_path.replace('\\', '/')
                try:
                    env.get_template(rel_path)
                except TemplateSyntaxError as e:
                    errors = True
                    print(f"Error in {rel_path}: {e}")
                    print(f"Line {e.lineno}")
                except Exception as e:
                    errors = True
                    print(f"Other error in {rel_path}: {e}")

    if not errors:
        print("All templates parsed successfully!")

if __name__ == '__main__':
    test_templates()
