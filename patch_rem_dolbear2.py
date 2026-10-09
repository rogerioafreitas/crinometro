filepath = 'utils/report_generator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """@dataclass
class ExportMetadata:
    resumo: bool = True
    metricas: bool = True
    cadencia: bool = True
    dolbear: bool = True
    lista_pulsos: bool = False"""
replacement = """@dataclass
class ExportMetadata:
    resumo: bool = True
    metricas: bool = True
    cadencia: bool = True
    lista_pulsos: bool = False"""
content = content.replace(target, replacement)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
