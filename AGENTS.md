# Diretrizes do Projeto — LojaVirtual (Vitrine Express)

## 1. Isolamento Total de Projeto
- Este repositório (`C:\Users\marco\projetos\LojaVirtual`) é um projeto **100% independente**.
- **NUNCA** acesse, leia ou modifique arquivos das pastas `C:\Users\marco\projetos\corretor` ou `C:\Users\marco\projetos\corretor-os`.
- **NUNCA** utilize skills globais voltadas para corretagem imobiliária (`agente-escreve-fila`, `agente-vendas-pipeline-diario`, `agente-vendas-whatsapp`, `sincroniza-salesforce`, `transcrever-audio-whatsapp`).

## 2. Como Conversar com o Marco
- O Marco não é programador de formação: explique decisões técnicas de forma simples, curta e prática, focando no resultado para o negócio.
- Vá sempre **um passo por vez**, alinhando cada etapa antes de despejar muitos detalhes técnicos.
- Evite perguntas desnecessárias quando houver uma recomendação clara e segura; sugira o melhor caminho diretamente.

## 3. Arquitetura e Status Atual (Vitrine Express)
- **Modelo de Negócio:** Vitrine de Afiliados Multimarcas (**Vitrine Express**) para Mercado Livre (`meli.la`), Shopee e Amazon.
- **Painel Local de Trabalho do Marco:** `http://localhost:8080/` (servido por `servidor_painel.py`, configurado para iniciar automaticamente com o Windows em `Startup\VitrineExpressServer.vbs` ou via `ABRIR_PAINEL_VITRINE.bat`).
- **Funcionalidades Prontas:**
  1. **Vitrine Pública (`index.html`, `styles.css`, `app.js`, `produtos.js`):** Busca rápida por código do vídeo (`#01`, `#10`), filtros de categoria e loja, ocultando botões administrativos na versão pública.
  2. **Importador Automático por Link (`/api/extrair`):** Extrai título, foto, preço exato (incluindo links curtos `meli.la`) e salva definitivamente em `produtos.js`, sincronizando via `git push` com o GitHub/Vercel.
  3. **Estúdio de Vídeo IA (`gerador_video.py`):** Gera vídeos verticais `.mp4` (9:16) com locução neural em português (`edge-tts` + `Pillow` + `FFmpeg`) e botão **"🚀 Postar no TikTok"** (copia legenda, abre pasta com vídeo selecionado e abre o TikTok Studio).
- **Repositório Remoto e Produção:** `https://github.com/mpaladinoGit/vitrine-express` conectado automaticamente à **Vercel** e ao **GitHub Pages**.
