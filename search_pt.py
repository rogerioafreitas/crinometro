with open('ui/main_window.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out = []
for i, line in enumerate(lines):
    if '"' in line or "'" in line:
        if any(word in line for word in ['Ativad', ' IA', 'Intelig', 'Modo', 'Salvar', 'Exportar', 'Gráfico', 'Selecione', 'Arquivo', 'Sobre', 'Config', 'Atualiz', 'Cancelar', 'Ajuda', 'Arquivo', 'Arquivos']):
            if 'import' not in line and 'print' not in line:
                out.append(f'{i+1}: {line.strip()[:100]}\n')

with open('pt_lines.txt', 'w', encoding='utf-8') as f:
    f.writelines(out)
