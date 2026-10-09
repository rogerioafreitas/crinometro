filepath = 'docs/ROADMAP_v4.5.0_ARCH_AND_EXPORTS_REV2.md'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("[ ] Listagem exaustiva de chilreios", "[x] Listagem exaustiva de chilreios")
content = content.replace("Próximo marco de implementação: executar a **FASE 9 - Relatório PDF modular**.", 
                          "**Status Atual:** Todas as FASES já foram concluídas (1 a 9). O estado atual do código é de revisão e correção de pendências finais.")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
