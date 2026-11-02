import asyncio
import io
import os
import re
import subprocess
import textwrap
import time
import urllib.request
import edge_tts
from PIL import Image, ImageDraw, ImageFont

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_VIDEOS = os.path.join(DIRETORIO_BASE, "videos_gerados")
os.makedirs(PASTA_VIDEOS, exist_ok=True)

LINK_CURTO_LOJA = "is.gd/vitrineexpress"


def obter_fonte(tamanho, negrito=False):
    caminhos = (
        [
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
        ]
        if negrito
        else [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
        ]
    )
    for c in caminhos:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, tamanho)
            except Exception:
                pass
    return ImageFont.load_default()


def formatar_moeda_br(valor):
    try:
        v = float(valor)
        inteiro = int(v)
        centavos = int(round((v - inteiro) * 100))
        inteiro_str = f"{inteiro:,}".replace(",", ".")
        return f"R$ {inteiro_str},{centavos:02d}"
    except Exception:
        return "R$ 0,00"


def formatar_preco_falado(valor):
    try:
        v = float(valor)
        reais = int(v)
        centavos = int(round((v - reais) * 100))
        if centavos > 0:
            return f"{reais} reais e {centavos} centavos"
        return f"{reais} reais"
    except Exception:
        return ""


def montar_roteiro_padrao(produto):
    titulo_completo = (produto.get("titulo") or "Produto em oferta").strip()
    palavras = titulo_completo.split()
    titulo_curto = " ".join(palavras[:8])
    plataforma_nome = produto.get("plataformaNome") or "Mercado Livre"
    codigo = str(produto.get("codigo") or "01")
    preco_atual = float(produto.get("precoAtual") or 0)
    preco_antigo = float(produto.get("precoAntigo") or 0)

    fala_preco = ""
    if preco_antigo > preco_atual and preco_atual > 0:
        fala_preco = (
            f"Caiu de {formatar_preco_falado(preco_antigo)} "
            f"para apenas {formatar_preco_falado(preco_atual)}! "
        )
    elif preco_atual > 0:
        fala_preco = f"Está saindo por apenas {formatar_preco_falado(preco_atual)}! "

    roteiro = (
        f"Olha esse achadinho que entrou em promoção no {plataforma_nome}! "
        f"{titulo_curto}. "
        f"{fala_preco}"
        f"Para garantir o seu com total segurança, acesse a nossa vitrine "
        f"e clique no botão verde para abrir direto no {plataforma_nome}!"
    )
    return roteiro


def montar_legenda_padrao(produto):
    titulo = (produto.get("titulo") or "Oferta Imperdível").strip()
    plataforma_nome = produto.get("plataformaNome") or "Mercado Livre"
    plataforma_tag = re.sub(r"\W+", "", plataforma_nome.lower())
    codigo = str(produto.get("codigo") or "01")
    preco_atual = formatar_moeda_br(produto.get("precoAtual") or 0)
    preco_antigo = float(produto.get("precoAntigo") or 0)
    atual_num = float(produto.get("precoAtual") or 0)

    linha_preco = f"💰 Por apenas {preco_atual}!"
    if preco_antigo > atual_num:
        linha_preco = f"💰 De {formatar_moeda_br(preco_antigo)} por apenas {preco_atual}!"

    return (
        f"🔥 Achadinho em promoção no {plataforma_nome}!\n\n"
        f"📦 {titulo}\n"
        f"{linha_preco}\n\n"
        f"👇 COMO COMPRAR NO SITE OFICIAL:\n"
        f"1️⃣ Acesse nossa vitrine: {LINK_CURTO_LOJA}\n"
        f"2️⃣ Clique no botão verde da oferta para abrir direto no {plataforma_nome}!\n\n"
        f"🔒 Compra 100% segura direto no app oficial ({plataforma_nome}).\n\n"
        f"#achadinhos #ofertas #{plataforma_tag} #promocao #desconto #vitrineexpress #dicasdecompras"
    )


def baixar_imagem_produto(url_img):
    if not url_img or not str(url_img).startswith("http"):
        return None
    try:
        req = urllib.request.Request(
            url_img,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            dados = resp.read(5_000_000)
            img = Image.open(io.BytesIO(dados)).convert("RGB")
            return img
    except Exception:
        return None


def desenhar_retangulo_arredondado(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def centralizar_texto(draw, W, y, texto, fonte, cor):
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), texto, font=fonte, fill=cor)


def criar_slide_cena(produto, img_produto, numero_cena):
    """
    Cria frames 720x1280 (9:16) sem depender de emojis de fonte (zero quadradinhos □),
    com endereço curto super legível para quem assiste no TikTok saber exatamente onde entrar.
    """
    W, H = 720, 1280
    base = Image.new("RGB", (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(base)

    for y in range(H):
        r = int(15 + (y / H) * 15)
        g = int(23 + (y / H) * 18)
        b = int(42 + (y / H) * 28)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    f_logo = obter_fonte(33, negrito=True)
    f_sub = obter_fonte(21, negrito=True)
    f_tag = obter_fonte(26, negrito=True)
    f_titulo = obter_fonte(28, negrito=True)
    f_preco_ant = obter_fonte(26, negrito=False)
    f_preco_atu = obter_fonte(56, negrito=True)
    f_link_gigante = obter_fonte(38, negrito=True)
    f_codigo_gigante = obter_fonte(54, negrito=True)

    # Topo da Marca
    desenhar_retangulo_arredondado(
        draw, (36, 36, W - 36, 126), 18, fill=(30, 41, 59), outline=(255, 106, 0), width=3
    )
    centralizar_texto(draw, W, 48, "VITRINE EXPRESS", f_logo, (255, 255, 255))
    plataforma_nome = (produto.get("plataformaNome") or "Mercado Livre").upper()
    centralizar_texto(draw, W, 88, f"OFERTA VERIFICADA • {plataforma_nome}", f_sub, (251, 191, 36))

    codigo = str(produto.get("codigo") or "01")
    preco_atual = float(produto.get("precoAtual") or 0)
    preco_antigo = float(produto.get("precoAntigo") or 0)
    desconto = 0
    if preco_antigo > preco_atual and preco_antigo > 0:
        desconto = int(round(((preco_antigo - preco_atual) / preco_antigo) * 100))

    textos_gancho = {
        1: ("SUPER ACHADINHO EM OFERTA!", (255, 85, 0)),
        2: ("PREÇO CAIU! APROVEITE HOJE", (22, 163, 74)),
        3: ("COMO COMPRAR COM SEGURANÇA:", (234, 88, 12)),
    }
    texto_topo, cor_topo = textos_gancho.get(numero_cena, textos_gancho[1])
    desenhar_retangulo_arredondado(draw, (50, 144, W - 50, 204), 14, fill=cor_topo)
    centralizar_texto(draw, W, 158, texto_topo, f_tag, (255, 255, 255))

    # Quadro da Foto do Produto
    card_top = 222
    card_bottom = 692
    desenhar_retangulo_arredondado(draw, (46, card_top, W - 46, card_bottom), 24, fill=(255, 255, 255))

    if img_produto:
        escala = 1.12 if numero_cena == 2 else (1.06 if numero_cena == 3 else 0.98)
        alvo_w = int(540 * escala)
        alvo_h = int(420 * escala)
        img_copia = img_produto.copy()
        img_copia.thumbnail((alvo_w, alvo_h), Image.Resampling.LANCZOS)
        px = (W - img_copia.width) // 2
        py = card_top + ((card_bottom - card_top) - img_copia.height) // 2
        base.paste(img_copia, (px, py))

    # Badge de Item #XX
    desenhar_retangulo_arredondado(draw, (66, card_top + 16, 235, card_top + 70), 12, fill=(15, 23, 42))
    draw.text((84, card_top + 26), f"ITEM #{codigo}", font=f_tag, fill=(251, 191, 36))

    # Badge de Desconto
    if desconto > 0:
        desenhar_retangulo_arredondado(draw, (W - 235, card_top + 16, W - 66, card_top + 70), 12, fill=(22, 163, 74))
        draw.text((W - 215, card_top + 26), f"-{desconto}% OFF", font=f_tag, fill=(255, 255, 255))

    # Título do Produto
    titulo = (produto.get("titulo") or "Produto em Oferta").strip()
    linhas_titulo = textwrap.wrap(titulo, width=35)[:2]
    y_t = 710
    for linha in linhas_titulo:
        centralizar_texto(draw, W, y_t, linha, f_titulo, (255, 255, 255))
        y_t += 36

    # Bloco de Preço (sempre visível em todas as cenas)
    desenhar_retangulo_arredondado(
        draw, (46, 795, W - 46, 975), 20, fill=(30, 41, 59), outline=(74, 222, 128), width=2
    )
    if preco_antigo > preco_atual:
        txt_ant = f"De {formatar_moeda_br(preco_antigo)}"
        bbox_a = draw.textbbox((0, 0), txt_ant, font=f_preco_ant)
        tw_a = bbox_a[2] - bbox_a[0]
        x_a = (W - tw_a) // 2
        draw.text((x_a, 808), txt_ant, font=f_preco_ant, fill=(148, 163, 184))
        draw.line([(x_a, 825), (x_a + tw_a, 825)], fill=(239, 68, 68), width=3)

    txt_atu = f"Por {formatar_moeda_br(preco_atual)}"
    centralizar_texto(draw, W, 842, txt_atu, f_preco_atu, (74, 222, 128))
    centralizar_texto(
        draw, W, 926, f"Compra 100% Segura no {produto.get('plataformaNome', 'Site Oficial')}", f_sub, (226, 232, 240)
    )

    # Bloco Inferior GIGANTE ensinando onde entrar para comprar!
    cor_box_cta = (22, 163, 74) if numero_cena == 3 else (255, 85, 0)
    desenhar_retangulo_arredondado(
        draw, (36, 995, W - 36, 1242), 22, fill=cor_box_cta, outline=(254, 240, 138), width=4
    )
    centralizar_texto(draw, W, 1012, "ACESSE NOSSA VITRINE OFICIAL:", f_sub, (255, 255, 255))

    # Caixa preta destacando o link curto fácil de digitar
    desenhar_retangulo_arredondado(draw, (66, 1048, W - 66, 1122), 14, fill=(15, 23, 42))
    centralizar_texto(draw, W, 1058, LINK_CURTO_LOJA, f_link_gigante, (251, 191, 36))

    centralizar_texto(draw, W, 1140, "CLIQUE NO BOTÃO VERDE DE COMPRA", f_tag, (255, 255, 255))
    centralizar_texto(draw, W, 1185, f"E ABRA DIRETO NO {plataforma_nome}!", f_sub, (254, 240, 138))

    return base


async def _salvar_audio_tts(texto, voz, caminho_mp3):
    comunicador = edge_tts.Communicate(texto, voz, rate="+8%")
    await comunicador.save(caminho_mp3)


def obter_duracao_audio(caminho_mp3):
    try:
        proc = subprocess.run(
            ["ffmpeg", "-i", caminho_mp3],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
        if m:
            horas = int(m.group(1))
            minutos = int(m.group(2))
            segundos = float(m.group(3))
            return horas * 3600 + minutos * 60 + segundos
    except Exception:
        pass
    return 12.0


def gerar_video_produto(produto, roteiro_custom="", voz="pt-BR-FranciscaNeural"):
    codigo = re.sub(r"\W+", "", str(produto.get("codigo") or "01"))
    timestamp = int(time.time())
    nome_base = f"vitrine_express_cod_{codigo}_{timestamp}"
    caminho_mp3 = os.path.join(PASTA_VIDEOS, f"{nome_base}.mp3")
    caminho_mp4 = os.path.join(PASTA_VIDEOS, f"{nome_base}.mp4")

    roteiro = (roteiro_custom or "").strip() or montar_roteiro_padrao(produto)
    legenda = montar_legenda_padrao(produto)

    # 1. Gera a narração em voz neural (Edge TTS)
    asyncio.run(_salvar_audio_tts(roteiro, voz, caminho_mp3))
    duracao = max(obter_duracao_audio(caminho_mp3) + 0.6, 6.0)

    # 2. Baixa a foto do produto e gera os 3 slides visuais limpos
    img_prod = baixar_imagem_produto(produto.get("imagem", ""))
    caminhos_slides = []
    for i in (1, 2, 3):
        slide = criar_slide_cena(produto, img_prod, i)
        caminho_s = os.path.join(PASTA_VIDEOS, f"{nome_base}_s{i}.png")
        slide.save(caminho_s, "PNG")
        caminhos_slides.append(caminho_s)

    # 3. Alterna as cenas mais rápido (a cada ~3s) para o vídeo ter movimento constante desde o início!
    passo = round(duracao / 4.0, 2)
    caminho_lista = os.path.join(PASTA_VIDEOS, f"{nome_base}_concat.txt")
    with open(caminho_lista, "w", encoding="utf-8") as f:
        f.write(f"file '{caminhos_slides[0].replace(os.sep, '/')}'\n")
        f.write(f"duration {passo}\n")
        f.write(f"file '{caminhos_slides[1].replace(os.sep, '/')}'\n")
        f.write(f"duration {passo}\n")
        f.write(f"file '{caminhos_slides[2].replace(os.sep, '/')}'\n")
        f.write(f"duration {passo}\n")
        f.write(f"file '{caminhos_slides[1].replace(os.sep, '/')}'\n")
        f.write(f"duration {passo + 0.5}\n")
        f.write(f"file '{caminhos_slides[2].replace(os.sep, '/')}'\n")

    # 4. Renderiza o MP4 com FPS contínuo (30fps) e Áudio 44100Hz Estéreo (exigido pelo TikTok para não dar "som indisponível"!)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        caminho_lista,
        "-i",
        caminho_mp3,
        "-vf",
        "fps=30,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        "-shortest",
        caminho_mp4,
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=True)

    for arq_temp in [*caminhos_slides, caminho_lista, caminho_mp3]:
        try:
            if os.path.exists(arq_temp):
                os.remove(arq_temp)
        except Exception:
            pass

    return {
        "sucesso": True,
        "arquivo": f"videos_gerados/{nome_base}.mp4",
        "caminhoCompleto": caminho_mp4,
        "roteiro": roteiro,
        "legenda": legenda,
        "duracao": round(duracao, 1),
    }
