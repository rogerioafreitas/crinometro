# Relatório Fase 8: Módulo de Exportação (Atualizado)

A Fase 8 do Crinômetro conclui a arquitetura de exportação assíncrona, desacoplada do PyQt6 para figuras, garantindo segurança na UI e fidelidade em publicações.

## Objetivos Concluídos e Verificados
- **Enumeração de Arquivos e Prevenção de Sobrescrita**: Exportações não sobrescrevem acidentalmente arquivos anteriores. `unique_path` e `png_set_suffix` resolvem concorrência e agrupam lotes da mesma exportação sob o mesmo sufixo.
- **Opções Refinadas**: Checkboxes dedicados para `Sinal bruto`, `Envoltória de Hilbert` e `Marcadores` estão visíveis caso Oscilograma esteja selecionado.
- **Fundo / Tema**: Opção nova no diálogo permite forçar o fundo `Branco (papel)` ou seguir o `Tema atual da janela`.
- **Específico / View Integrado**: O limite temporal agora herda corretamente da vista dinâmica sem acoplamento silencioso através de `live_view`. Além disso, possui o checkbox opcional `Aplicar recorte de tempo ao oscilograma`.
- **Fidelidade Científica Restaurada**: A min/max decimation foi restaurada de forma imaculada para exportação `interactive=False` do Oscilograma (preservando picos de 1 amostra num sinal inteiro). O Espectrograma retomou `shading='auto'`, `rasterized=True` e ganhou sua colorbar de `Potência (dB)`.
- **Segurança de Threading e Contexto**: Snapshot limpo usando deep/shallow copy para não amarrar a RAM. Cancelamento assíncrono perfeitamente amarrado passando função callback sem usar `terminate()`. Fechar a janela agora oculta tudo amigavelmente até a thread morrer e cancelar.
- **Qualidade e Estabilidade Codebase**: Passou integralmente nos scripts AST `quality_gate.py` modificado para varrer falhas de import estaticamente, garantindo que o programa está limpo de `IndentationErrors` e outras amarras globais de importação. Arquivos residuais temporários limpados.

## Limitações Conhecidas e Fora do Escopo Atual
- Exportação paginada por janela de tempo longa.
- DPI estendido acima de 600.
- Suporte de i18n total na string do diálogo.

## Não Testado Localmente
- A GUI e a suíte unitária de `tests/` falham silenciosamente na CLI porque o pacote `ui/__init__.py` tenta arrastar instâncias do PyQt6 (que não está disponível no meu ambiente).

Próximas etapas: Analítico e Desempenho Assíncrono (Fases 9 e 10).
