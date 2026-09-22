"""Embed the maintained controller HTML in the platform-only Android build."""
import json,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
p=root/'src/dev/atul/capsulemap/MainActivity.java'
s=p.read_text();start=s.index('  static final String HTML=')
p.write_text(s[:start]+'  static final String HTML='+json.dumps((root/'web/controller.html').read_text())+';\n}\n')
