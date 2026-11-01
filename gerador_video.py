import asyncio
import io
import os
import re
import subprocess
import textwrap
import time
import urllib.request
from PIL import Image, ImageDraw, ImageFont

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_VIDEOS = os.path.join(DIRETORIO_BASE, "videos_gerados")
os.makedirs(PASTA_VIDEOS, exist_ok=True)


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
    # Pega as primeiras 8 palavras para a fala ficar fluida e natural
    palavras = titulo_completo.split()
    titulo_curto = " ".join(palavras[:8])
    plataforma_nome = produto.get("plataformaNome") or "Loja Oficial"
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
        f"Olha esse achadinho que acabou de entrar em promoção no {plataforma_nome}! "
        f"{titulo_curto}. "
        f"{fala_preco}"
        f"Para garantir o seu no aplicativo oficial, clique no link da bio da Vitrine Express "
        f"e digite o código {codigo}!"
    )
    return roteiro


def montar_legenda_padrao(produto):
    titulo = (produto.get("titulo") or "Oferta Imperdível").strip()
    plataforma_nome = produto.get("plataformaNome") or "Loja Oficial"
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
        f"👇 COMO ENCONTRAR O LINK OFICIAL:\n"
        f"1️⃣ Acesse nossa vitrine no perfil: vitrine-express-ten.vercel.app\n"
        f"2️⃣ Digite o código #{codigo} na busca!\n\n"
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


def criar_slide_cena(produto, img_produto, numero_cena):
    """
    Cria um frame vertical 720x1280 (9:16) para cada momento do vídeo:
    Cena 1: Gancho + Foto Grande + Desconto
    Cena 2: Destaque de Preço De/Por + Economia
    Cena 3: Chamada Final (Link na Bio + Código #XX)
    """
    W, H = 720, 1280
    base = Image.new("RGB", (W, H), (15, 23, 42))
    draw = ImageDraw.Draw(base)

    # Gradiente sutil de fundo
    for y in range(H):
        r = int(15 + (y / H) * 15)
        g = int(23 + (y / H) * 18)
        b = int(42 + (y / H) * 28)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    f_logo = obter_fonte(34, negrito=True)
    f_sub = obter_fonte(20, negrito=False)
    f_tag = obter_fonte(26, negrito=True)
    f_titulo = obter_fonte(30, negrito=True)
    f_preco_ant = obter_fonte(28, negrito=False)
    f_preco_atu = obter_fonte(58, negrito=True)
    f_cta_grande = obter_fonte(44, negrito=True)
    f_codigo_gigante = obter_fonte(66, negrito=True)

    # Topo da Marca
    desenhar_retangulo_arredondado(draw, (40, 42, W - 40, 130), 20, fill=(30, 41, 59), outline=(255, 106, 0), width=2)
    draw.text((70, 58), "⚡ VITRINE EXPRESS", font=f_logo, fill=(255, 255, 255))
    plataforma_nome = (produto.get("plataformaNome") or "Mercado Livre").upper()
    draw.text((70, 96), f"Oferta Verificada • {plataforma_nome}", font=f_sub, fill=(251, 191, 36))

    codigo = str(produto.get("codigo") or "01")
    preco_atual = float(produto.get("precoAtual") or 0)
    preco_antigo = float(produto.get("precoAntigo") or 0)
    desconto = 0
    if preco_antigo > preco_atual and preco_antigo > 0:
        desconto = int(round(((preco_antigo - preco_atual) / preco_antigo) * 100))

    # Banner superior de gancho conforme a cena
    textos_gancho = {
        1: ("🔥 ACHADINHO EM OFERTA!", (255, 85, 0)),
        2: ("💸 OLHA ESSE DESCONTO!", (22, 163, 74)),
        3: ("👇 GARANTA O SEU AGORA!", (234, 88, 12)),
    }
    texto_topo, cor_topo = textos_gancho.get(numero_cena, textos_gancho[1])
    desenhar_retangulo_arredondado(draw, (60, 152, W - 60, 214), 16, fill=cor_topo)
    bbox_g = draw.textbbox((0, 0), texto_topo, font=f_tag)
    tw_g = bbox_g[2] - bbox_g[0]
    draw.text(((W - tw_g) // 2, 167), texto_topo, font=f_tag, fill=(255, 255, 255))

    # Quadro da Foto do Produto
    card_top = 236
    card_bottom = 746
    desenhar_retangulo_arredondado(draw, (50, card_top, W - 50, card_bottom), 26, fill=(255, 255, 255))

    if img_produto:
        # Na cena 2 damos um leve zoom na imagem para dar movimento entre os cortes
        escala = 1.08 if numero_cena == 2 else (1.04 if numero_cena == 3 else 1.0)
        alvo_w = int(560 * escala)
        alvo_h = int(450 * escala)
        img_copia = img_produto.copy()
        img_copia.thumbnail((alvo_w, alvo_h), Image.Resampling.LANCZOS)
        px = (W - img_copia.width) // 2
        py = card_top + ((card_bottom - card_top) - img_copia.height) // 2
        base.paste(img_copia, (px, py))

    # Badge de Código #XX no canto superior esquerdo da foto
    desenhar_retangulo_arredondado(draw, (70, card_top + 18, 235, card_top + 74), 14, fill=(15, 23, 42))
    draw.text((88, card_top + 28), f"CÓD #{codigo}", font=f_tag, fill=(251, 191, 36))

    # Badge de Desconto no canto superior direito da foto
    if desconto > 0:
        desenhar_retangulo_arredondado(draw, (W - 235, card_top + 18, W - 70, card_top + 74), 14, fill=(22, 163, 74))
        draw.text((W - 215, card_top + 28), f"-{desconto}% OFF", font=f_tag, fill=(255, 255, 255))

    # Título do Produto (abaixo da foto)
    titulo = (produto.get("titulo") or "Produto em Oferta").strip()
    linhas_titulo = textwrap.wrap(titulo, width=34)[:2]
    y_t = 768
    for linha in linhas_titulo:
        bbox_l = draw.textbbox((0, 0), linha, font=f_titulo)
        tw_l = bbox_l[2] - bbox_l[0]
        draw.text(((W - tw_l) // 2, y_t), linha, font=f_titulo, fill=(255, 255, 255))
        y_t += 38

    # Bloco Inferior: muda o destaque entre Preço (Cenas 1 e 2) e Chamada Link na Bio (Cena 3)
    if numero_cena in (1, 2):
        desenhar_retangulo_arredondado(
            draw, (50, 865, W - 50, 1065), 22, fill=(30, 41, 59), outline=(71, 85, 105), width=2
        )
        if preco_antigo > preco_atual:
            txt_ant = f"De {formatar_moeda_br(preco_antigo)}"
            bbox_a = draw.textbbox((0, 0), txt_ant, font=f_preco_ant)
            tw_a = bbox_a[2] - bbox_a[0]
            x_a = (W - tw_a) // 2
            draw.text((x_a, 882), txt_ant, font=f_preco_ant, fill=(148, 163, 184))
            draw.line([(x_a, 900), (x_a + tw_a, 900)], fill=(239, 68, 68), width=3)

        txt_atu = f"Por {formatar_moeda_br(preco_atual)}"
        bbox_p = draw.textbbox((0, 0), txt_atu, font=f_preco_atu)
        tw_p = bbox_p[2] - bbox_p[0]
        draw.text(((W - tw_p) // 2, 922), txt_atu, font=f_preco_atu, fill=(74, 222, 128))

        txt_seg = f"🔒 Compra 100% Segura no {produto.get('plataformaNome', 'Site Oficial')}"
        bbox_s = draw.textbbox((0, 0), txt_seg, font=f_sub)
        tw_s = bbox_s[2] - bbox_s[0]
        draw.text(((W - tw_s) // 2, 1012), txt_seg, font=f_sub, fill=(226, 232, 240))

        # Rodapé de chamada
        desenhar_retangulo_arredondado(draw, (50, 1090, W - 50, 1225), 20, fill=(255, 85, 0))
        txt_c1 = "🔗 LINK NA BIO DA VITRINE EXPRESS"
        bbox_c1 = draw.textbbox((0, 0), txt_c1, font=f_tag)
        draw.text(((W - (bbox_c1[2] - bbox_c1[0])) // 2, 1112), txt_c1, font=f_tag, fill=(255, 255, 255))

        txt_c2 = f"Digite o código #{codigo} na busca!"
        bbox_c2 = draw.textbbox((0, 0), txt_c2, font=f_titulo)
        draw.text(((W - (bbox_c2[2] - bbox_c2[0])) // 2, 1156), txt_c2, font=f_titulo, fill=(254, 240, 138))
    else:
        # Cena 3: Chamada Gigante para o Código na Bio
        desenhar_retangulo_arredondado(
            draw, (45, 860, W - 45, 1225), 26, fill=(255, 85, 0), outline=(251, 191, 36), width=4
        )
        t1 = "PASSO 1: CLIQUE NO LINK DA BIO"
        b1 = draw.textbbox((0, 0), t1, font=f_tag)
        draw.text(((W - (b1[2] - b1[0])) // 2, 892), t1, font=f_tag, fill=(255, 255, 255))

        t2 = "PASSO 2: DIGITE O NÚMERO:"
        b2 = draw.textbbox((0, 0), t2, font=f_titulo)
        draw.text(((W - (b2[2] - b2[0])) // 2, 945), t2, font=f_titulo, fill=(254, 240, 138))

        desenhar_retangulo_arredondado(draw, (140, 1005, W - 140, 1135), 22, fill=(15, 23, 42))
        t_cod = f"#{codigo}"
        bc = draw.textbbox((0, 0), t_cod, font=f_codigo_gigante)
        draw.text(((W - (bc[2] - bc[0])) // 2, 1022), t_cod, font=f_codigo_gigante, fill=(251, 191, 36))

        t3 = f"E abra direto no {produto.get('plataformaNome', 'App Oficial')}!"
        b3 = draw.textbbox((0, 0), t3, font=f_sub)
        draw.text(((W - (b3[2] - b3[0])) // 2, 1162), t3, font=f_sub, fill=(255, 255, 255))

    return base


async def _salvar_audio_tts(texto, voz, caminho_mp3):
    comunicador = edge_tts.Communicate(texto, voz, rate="+8%")
    await comunicador.save(caminho_mp3)


import edge_tts


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

    # 2. Baixa a foto do produto e gera os 3 slides visuais (Gancho -> Preço -> Chamada Código)
    img_prod = baixar_imagem_produto(produto.get("imagem", ""))
    caminhos_slides = []
    for i in (1, 2, 3):
        slide = criar_slide_cena(produto, img_prod, i)
        caminho_s = os.path.join(PASTA_VIDEOS, f"{nome_base}_s{i}.png")
        slide.save(caminho_s, "PNG")
        caminhos_slides.append(caminho_s)

    # 3. Cria arquivo de concatenação do FFmpeg dividindo o tempo entre as 3 cenas
    t1 = round(duracao * 0.36, 2)
    t2 = round(duracao * 0.34, 2)
    t3 = round(duracao - t1 - t2 + 0.4, 2)
    caminho_lista = os.path.join(PASTA_VIDEOS, f"{nome_base}_concat.txt")
    with open(caminho_lista, "w", encoding="utf-8") as f:
        f.write(f"file '{caminhos_slides[0].replace(os.sep, '/')}'\n")
        f.write(f"duration {t1}\n")
        f.write(f"file '{caminhos_slides[1].replace(os.sep, '/')}'\n")
        f.write(f"duration {t2}\n")
        f.write(f"file '{caminhos_slides[2].replace(os.sep, '/')}'\n")
        f.write(f"duration {t3}\n")
        f.write(f"file '{caminhos_slides[2].replace(os.sep, '/')}'\n")

    # 4. Renderiza o MP4 H.264 + AAC pronto para TikTok / Instagram Reels
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
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "24",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        caminho_mp4,
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45, check=True)

    # Remove arquivos temporários de slides e áudio solto
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
