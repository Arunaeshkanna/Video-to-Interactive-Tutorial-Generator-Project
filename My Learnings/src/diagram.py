from __future__ import annotations

import html


def mermaid_block_to_html(code: str) -> str:
    escaped = html.escape(code)
    return f"""
    <html>
      <head>
        <script type="module">
          import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
          mermaid.initialize({{ startOnLoad: true, theme: 'base', securityLevel: 'loose' }});
        </script>
        <style>
          body {{
            margin: 0;
            min-height: 380px;
            display: grid;
            place-items: center;
            background: linear-gradient(135deg, #ffffff, #f2faf8);
            border: 1px solid rgba(18,32,47,.12);
            border-radius: 8px;
            font-family: Inter, Segoe UI, sans-serif;
          }}
          .mermaid {{
            width: 100%;
            display: grid;
            place-items: center;
          }}
        </style>
      </head>
      <body>
        <pre class="mermaid">{escaped}</pre>
      </body>
    </html>
    """
