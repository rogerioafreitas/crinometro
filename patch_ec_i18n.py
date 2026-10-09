filepath = 'ui/controllers/editor_controller.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = 'win.lbl_metric_sub.setText("Moda: -   |   Média: -")'
replacement = 'win.lbl_metric_sub.setText(f\'{I18N[win.lang]["mean"]}: -   |   {I18N[win.lang]["variance"]}: -\')'
content = content.replace(target, replacement)

# Also fix the valid metric string!
target2 = 'win.lbl_metric_sub.setText(f"Média: {media:.2f}   |   Variância: {variancia:.2f}")'
replacement2 = 'win.lbl_metric_sub.setText(f\'{I18N[win.lang]["mean"]}: {media:.2f}   |   {I18N[win.lang]["variance"]}: {variancia:.2f}\')'
content = content.replace(target2, replacement2)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
