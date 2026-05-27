# Design — Reorganização profissional + rebrand `visus-desktop`

**Data:** 2026-05-27
**Autor:** Matheus Pereira (com Claude)
**Status:** aprovado (decisões fechadas via brainstorming)

## Contexto e objetivo

A biblioteca hoje publicada no PyPI como `bot-vision-suite` (v1.3.1, import `bot_vision`)
vive dentro de `D:\bot_vision\new\bot_vision_suite\bot_vision_suite\`, num repositório git que
**mistura a lib com scripts pessoais de RPA** (`a.py`, `test.py`). O código tem arquivos
espalhados, configs duplicadas, lixo e testes quebrados.

Objetivo: extrair a biblioteca para um **repositório próprio, limpo e profissional**, no padrão
de bibliotecas grandes (src/ layout, namespace package, tooling de qualidade), **sem quebrar
funcionalidades**, e rebrandear como o primeiro produto de uma família de marca.

## Estratégia de marca (decidida)

Marca-mãe **Visus** (todo o namespace `visus-*` está livre no PyPI). Família planejada:

| Produto | Distribuição PyPI | Import | Papel |
|---|---|---|---|
| **Esta lib** | `visus-desktop` | `visus.desktop` | Automação desktop (visão/OCR) |
| Futuro | `visus-web` | `visus.web` | Automação web (estilo Selenium/BotCity) |
| Futuro | `visus-core` | `visus.core` | Tipos/utils compartilhados (opcional) |
| Futuro (SaaS) | — | — | **Visus Cloud** — orquestração de RPA |

Mecanismo técnico: **namespace package PEP 420** — `src/visus/` **sem** `__init__.py`, de modo
que `visus.desktop` e (futuramente) `visus.web` possam ser instalados separadamente e conviver
sob `import visus.*` (padrão `google.cloud.*`).

A classe principal `BotVision` passa a se chamar **`VisusBot`** (`from visus.desktop import VisusBot`),
com **alias `BotVision = VisusBot`** mantido para compatibilidade.

## Localização (decidida)

Novo repositório limpo em **`D:\bot_vision\visus-desktop\`**, com `git init` próprio.
O ambiente atual (`new/bot_vision_suite/` com `a.py`, `test.py`) **fica intacto**.
A fonte da verdade do código é `new\bot_vision_suite\bot_vision_suite\bot_vision\` + arquivos de apoio.

## Estrutura-alvo

```
visus-desktop/
├── .github/workflows/
│   ├── test.yml                 # CI de testes (matriz de Python), atualizado p/ visus-desktop
│   └── publish.yml              # publicação PyPI, atualizado
├── src/
│   └── visus/                   # SEM __init__.py  (namespace PEP 420)
│       └── desktop/             # antigo pacote bot_vision/
│           ├── __init__.py      # API pública (VisusBot + alias BotVision, funções standalone)
│           ├── py.typed         # NOVO — marca o pacote como tipado
│           ├── exceptions.py
│           ├── core/
│           │   ├── __init__.py
│           │   ├── image_processing.py
│           │   ├── keyboard_commands.py
│           │   ├── ocr_engine.py
│           │   ├── overlay.py
│           │   ├── relative_image.py
│           │   ├── task_executor.py
│           │   ├── virtual_mouse.py
│           │   └── wait_manager.py
│           └── utils/
│               ├── __init__.py
│               ├── config.py
│               └── text_filters.py
├── tests/                       # consertados + nomes EN
├── examples/                    # nomes EN
├── docs/                        # api_reference, installation, README (refeitos p/ novo nome)
├── scripts/                     # build_package.py, check_dependencies.py, update_pypi.ps1, validate_package.py
├── pyproject.toml               # fonte única de config
├── .pre-commit-config.yaml      # NOVO — ruff + mypy
├── .gitignore
├── README.md
├── CHANGELOG.md
├── LICENSE
├── CONTRIBUTING.md              # NOVO
├── SECURITY.md                  # NOVO
└── CODE_OF_CONDUCT.md           # NOVO
```

Notas:
- Build artifacts (`build/`, `dist/`, `*.egg-info/`) **não** são copiados (são gerados).
- `docs/superpowers/` (este spec) é planejamento interno → entra no `.gitignore`, não é publicado.

## Mudanças detalhadas

### 1. Rebrand `bot_vision` → `visus.desktop`
- Imports **internos** são relativos (`from .`, `from ..`) → **não mudam** com a realocação.
- Imports **absolutos** (`from bot_vision...`, `import bot_vision`) existem só em tests/examples/docs/README → atualizar para `visus.desktop`.
- `class BotVision` → `class VisusBot`; ao final do módulo: `BotVision = VisusBot` (alias compat).
- Logging usa `__name__` → atualiza sozinho. Strings de versão/branding ("Bot Vision Suite v1.3.0") → atualizar.

### 2. src/ layout + namespace
- Mover pacote para `src/visus/desktop/`. **Não** criar `src/visus/__init__.py`.
- `pyproject.toml`: `[tool.setuptools.packages.find] where = ["src"]`, `include = ["visus*"]`.

### 3. Remoção de lixo
- `0.37.0` (saída de pip salva como arquivo), `core/overlay_new.py` (0 bytes), `build/`, `dist/`, `*.egg-info/`.

### 4. Config unificada no pyproject
- Remover `pytest.ini` (migrar markers/addopts p/ `[tool.pytest.ini_options]`).
- Remover `requirements.txt` (deps já em `[project.dependencies]`).
- Remover ou corrigir `MANIFEST.in` (hoje referencia `INSTALL.md`/`PUBLISH_CHECKLIST.md` inexistentes); com src-layout + setuptools, provavelmente desnecessário.
- Deduplicar `[dependency-groups]` × `[project.optional-dependencies]` (manter um padrão; usar optional-dependencies + dependency-groups só p/ dev).
- Cobertura: `--cov=visus.desktop`.

### 5. Tooling de qualidade
- **ruff** (lint + format; substitui black/flake8/isort) — config em `pyproject.toml`.
- **mypy** — config em `pyproject.toml` (modo gradual; não obrigatório passar 100% já).
- **pre-commit** — `.pre-commit-config.yaml` com ruff + ruff-format (+ mypy opcional).
- **py.typed** — arquivo vazio no pacote, declarado nos package-data.

### 6. Conserto dos testes (suíte hoje quebrada)
- `test_exceptions.py`: `OCRError` → `OCRProcessingError` (e demais nomes reais de `exceptions.py`).
- `test_integration.py`: `from bot_visions0 import ...` → `from visus.desktop import ...`.
- `test_utils.py`: `clean_text` não existe; função real é `limpar_texto`. **Renomear** `limpar_texto`→`clean_text` (alias `limpar_texto = clean_text` p/ compat) e atualizar imports no `__init__.py`/teste.
- Todos os `from bot_vision...` nos testes → `from visus.desktop...`.
- Meta: `pytest` **verde** ao final (executado em venv com instalação editável).

### 7. Normalização de nomes PT → EN
- tests: `teste_cores_overlay.py` → `test_overlay_colors.py`.
- examples: `exemplo_overlay_config.py` → `overlay_config_example.py`; revisar `migration_guide*`/`new_features_example` p/ nomes claros.
- Docstrings e comentários em PT **permanecem** (decisão: só os nomes de arquivo/símbolos públicos são normalizados).

### 8. Higiene de API
- Corrigir `__all__` **duplicado** no `__init__.py` (duas definições; a 2ª sobrescreve a 1ª) → uma lista única e correta.
- Corrigir `SyntaxWarning: invalid escape sequence '\P'` no docstring do `__init__.py` (usar raw string `r"""`).

### 9. Arquivos de comunidade e docs
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` (templates padrão, em PT ou EN — EN recomendado p/ alcance).
- `README.md`, `docs/*` e `CHANGELOG.md` atualizados p/ `visus-desktop` / `pip install visus-desktop` / `from visus.desktop import VisusBot`.

### 10. Versionamento e publicação
- Pacote novo → começar em **`0.1.0`** (sinaliza projeto novo sob a marca). `CHANGELOG` ganha seção `[0.1.0]` descrevendo o rebrand e migração.
- **Não publicar** no PyPI neste trabalho — só deixar pronto. Publicação é passo manual posterior do usuário.
- `bot-vision-suite` 1.3.1 permanece no PyPI como está (não removido).

## Fora de escopo (YAGNI)
- Quebrar o `__init__.py` gigante (~2500 linhas) em módulos — melhoria desejável, mas arriscada; fica para depois.
- Implementar `visus-web` / `visus-core` / Visus Cloud — projetos futuros, specs próprios.
- Publicar no PyPI.

## Estratégia "sem quebrar funcionalidades"
1. Baseline: hoje a suíte **não** passa (4 erros de coleção por imports errados). Não há verde a preservar — vamos **deixar verde**.
2. Trabalhar em venv dedicado com `pip install -e .` apontando para o novo `src/` layout.
3. Rodar `pytest` após cada fase grande (rebrand de imports, conserto de testes, config).
4. Alias `BotVision = VisusBot` e `limpar_texto = clean_text` garantem compatibilidade de API.
5. Tudo versionado em git (commits por fase) → reversível.

## Critérios de aceitação
- [ ] `D:\bot_vision\visus-desktop\` existe como repo git limpo, sem scripts pessoais.
- [ ] `pip install -e .` instala e `python -c "from visus.desktop import VisusBot, BotVision"` funciona.
- [ ] `import visus.desktop` resolve via namespace package (sem `visus/__init__.py`).
- [ ] `pytest` passa (suíte verde).
- [ ] `ruff check` e `ruff format --check` configurados e passando (ou com baseline documentado).
- [ ] Sem arquivos de lixo / configs duplicadas; estrutura igual à "Estrutura-alvo".
- [ ] README/docs/CHANGELOG refletem `visus-desktop`.
- [ ] `a.py` do usuário continua funcionando trocando só o import para `from visus.desktop import BotVision`.
