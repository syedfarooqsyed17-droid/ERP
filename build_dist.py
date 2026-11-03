import os

def build():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    jsx_path = os.path.join(base_dir, 'Frontend', 'interface.jsx')
    
    with open(jsx_path, 'r', encoding='utf-8') as f:
        jsx_code = f.read()

    header = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>NEXUS ERP & CRM Platform</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏢</text></svg>">
  
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: {
              50: '#eef2ff',
              500: '#6366f1',
              600: '#4f46e5',
              700: '#4338ca'
            }
          }
        }
      }
    };
  </script>
  
  <!-- Babel Standalone for In-Browser JSX Compilation -->
  <script src="https://unpkg.com/@babel/standalone@7.24.0/babel.min.js"></script>

  <!-- ES Module Import Map for React & Lucide Icons -->
  <script type="importmap">
  {
    "imports": {
      "react": "https://esm.sh/react@18.2.0",
      "react/": "https://esm.sh/react@18.2.0/",
      "react-dom": "https://esm.sh/react-dom@18.2.0",
      "react-dom/client": "https://esm.sh/react-dom@18.2.0/client",
      "lucide-react": "https://esm.sh/lucide-react@0.344.0"
    }
  }
  </script>

  <style>
    /* Sleek custom dark scrollbar */
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-track {
      background: #090d16;
    }
    ::-webkit-scrollbar-thumb {
      background: #1e293b;
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #334155;
    }
    @keyframes spin-slow {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  </style>
</head>
<body class="bg-slate-900 text-slate-100 antialiased overflow-hidden">
  <div id="root">
    <div style="min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; background-color: #020617; color: #94a3b8; font-family: ui-sans-serif, system-ui, sans-serif;">
      <div style="width: 48px; height: 48px; border: 3px solid #312e81; border-top-color: #6366f1; border-radius: 50%; animation: spin-slow 1s linear infinite; margin-bottom: 16px;"></div>
      <h2 style="color: #f8fafc; font-size: 1.125rem; font-weight: 600; margin-bottom: 4px;">Loading NEXUS ERP Platform</h2>
      <p style="font-size: 0.875rem; color: #64748b;">Initializing 10,000 product catalog & ERP subsystems...</p>
    </div>
  </div>

  <script type="text/babel" data-type="module">
  import ReactDOM from 'react-dom/client';
"""

    footer = """
  const root = ReactDOM.createRoot(document.getElementById('root'));
  root.render(<App />);
  </script>
</body>
</html>
"""

    full_html = header + "\n" + jsx_code + "\n" + footer

    # Update index.html, Frontend/interface.html, and Frontend/index.html
    paths = [
        os.path.join(base_dir, 'index.html'),
        os.path.join(base_dir, 'Frontend', 'interface.html'),
        os.path.join(base_dir, 'Frontend', 'index.html')
    ]
    for p in paths:
        with open(p, 'w', encoding='utf-8') as f:
            f.write(full_html)

    print("Successfully built index.html, Frontend/interface.html, and Frontend/index.html from interface.jsx")

if __name__ == '__main__':
    build()

