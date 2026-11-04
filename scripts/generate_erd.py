import os
from PIL import Image, ImageDraw, ImageFont

def generate_erd():
    WIDTH = 2400
    HEIGHT = 1400

    img = Image.new("RGB", (WIDTH, HEIGHT), color="#0b1120")
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 30)
        font_subtitle = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 15)
        font_tbl_header = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 17)
        font_col = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)
        font_badge = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 10)
        font_legend = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 13)
        font_cardinality = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 12)
    except Exception:
        font_title = font_subtitle = font_tbl_header = font_col = font_badge = font_legend = font_cardinality = ImageFont.load_default()

    # Draw background subtle grid
    grid_color = "#131c31"
    for x in range(0, WIDTH, 40):
        draw.line([(x, 0), (x, HEIGHT)], fill=grid_color, width=1)
    for y in range(0, HEIGHT, 40):
        draw.line([(0, y), (WIDTH, y)], fill=grid_color, width=1)

    # Header Panel
    draw.rounded_rectangle([(50, 30), (WIDTH - 50, 120)], radius=12, fill="#131d35", outline="#223354", width=2)
    draw.line([(50, 118), (WIDTH - 50, 118)], fill="#38bdf8", width=3)
    draw.text((80, 42), "DICOEVENT VERSI 1 — ENTITY RELATIONSHIP DIAGRAM (ERD)", fill="#ffffff", font=font_title)
    draw.text((82, 85), "Normalized Relational PostgreSQL Database Schema • UUID Primary Keys • Foreign Key Cascades • RBAC Multi-Tenancy", fill="#94a3b8", font=font_subtitle)

    # Table definitions
    # (name, header_color, x, y, width, columns: [(name, type, badge)])
    tables = [
        {
            "id": "auth_group",
            "name": "auth_group",
            "cat": "IDENTITY & RBAC",
            "header_color": "#312e81",
            "x": 80,
            "y": 160,
            "w": 400,
            "cols": [
                ("id", "INT", "PK"),
                ("name", "VARCHAR(150)", "UQ"),
            ]
        },
        {
            "id": "users_groups",
            "name": "users_groups",
            "cat": "RBAC MEMBERSHIP",
            "header_color": "#3730a3",
            "x": 560,
            "y": 160,
            "w": 440,
            "cols": [
                ("id", "BIGINT", "PK"),
                ("user_id", "UUID", "FK"),
                ("group_id", "INT", "FK"),
            ]
        },
        {
            "id": "users",
            "name": "users",
            "cat": "AUTHENTICATION & USERS",
            "header_color": "#1e3a8a",
            "x": 80,
            "y": 380,
            "w": 400,
            "cols": [
                ("id", "UUID", "PK"),
                ("username", "VARCHAR(150)", "UQ"),
                ("email", "VARCHAR(254)", "UQ"),
                ("password", "VARCHAR(128)", ""),
                ("first_name", "VARCHAR(150)", ""),
                ("last_name", "VARCHAR(150)", ""),
                ("is_superuser", "BOOLEAN", ""),
                ("is_staff", "BOOLEAN", ""),
                ("is_active", "BOOLEAN", ""),
                ("date_joined", "TIMESTAMP", ""),
            ]
        },
        {
            "id": "events",
            "name": "events",
            "cat": "EVENT MANAGEMENT",
            "header_color": "#065f46",
            "x": 560,
            "y": 380,
            "w": 460,
            "cols": [
                ("id", "UUID", "PK"),
                ("name", "VARCHAR(255)", ""),
                ("description", "TEXT", ""),
                ("location", "VARCHAR(255)", ""),
                ("start_time", "TIMESTAMP", ""),
                ("end_time", "TIMESTAMP", ""),
                ("status", "VARCHAR(50)", ""),
                ("quota", "INT", ""),
                ("category", "VARCHAR(100)", ""),
                ("organizer_id", "UUID", "FK"),
            ]
        },
        {
            "id": "event_posters",
            "name": "event_posters",
            "cat": "MEDIA & OBJECT STORAGE",
            "header_color": "#0f766e",
            "x": 560,
            "y": 880,
            "w": 460,
            "cols": [
                ("id", "UUID", "PK"),
                ("event_id", "UUID", "FK"),
                ("image", "VARCHAR(255)", ""),
            ]
        },
        {
            "id": "tickets",
            "name": "tickets",
            "cat": "TICKETING & PRICING",
            "header_color": "#7c2d12",
            "x": 1100,
            "y": 380,
            "w": 440,
            "cols": [
                ("id", "UUID", "PK"),
                ("event_id", "UUID", "FK"),
                ("name", "VARCHAR(255)", ""),
                ("price", "INT", ""),
                ("sales_start", "TIMESTAMP", ""),
                ("sales_end", "TIMESTAMP", ""),
                ("quota", "INT", ""),
            ]
        },
        {
            "id": "registrations",
            "name": "registrations",
            "cat": "ATTENDEE REGISTRATIONS",
            "header_color": "#6b21a8",
            "x": 1620,
            "y": 380,
            "w": 440,
            "cols": [
                ("id", "UUID", "PK"),
                ("ticket_id", "UUID", "FK"),
                ("user_id", "UUID", "FK"),
            ]
        },
        {
            "id": "payments",
            "name": "payments",
            "cat": "PAYMENTS & BILLING",
            "header_color": "#831843",
            "x": 1620,
            "y": 660,
            "w": 440,
            "cols": [
                ("id", "UUID", "PK"),
                ("registration_id", "UUID", "FK"),
                ("payment_method", "VARCHAR(100)", ""),
                ("payment_status", "VARCHAR(100)", ""),
                ("amount_paid", "INT", ""),
            ]
        },
    ]

    # Precalculate table heights and bounding boxes
    ROW_H = 26
    HEADER_H = 48
    tbl_rects = {}

    for tbl in tables:
        x = tbl["x"]
        y = tbl["y"]
        w = tbl["w"]
        h = HEADER_H + len(tbl["cols"]) * ROW_H + 10
        tbl_rects[tbl["id"]] = (x, y, w, h)

    # Helper function for drawing rounded badges
    def draw_badge(x, y, text, b_type):
        colors = {
            "PK": ("#b45309", "#fef3c7"),
            "FK": ("#0369a1", "#e0f2fe"),
            "UQ": ("#6d28d9", "#ede9fe"),
        }
        bg, fg = colors.get(b_type, ("#374151", "#f9fafb"))
        bw, bh = 26, 16
        draw.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=4, fill=bg)
        draw.text((x + 5, y + 2), text, fill=fg, font=font_badge)

    # Draw tables
    for tbl in tables:
        x, y, w, h = tbl_rects[tbl["id"]]

        # Outer card with shadow & border
        draw.rounded_rectangle([(x + 4, y + 4), (x + w + 4, y + h + 4)], radius=10, fill="#070c18")
        draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=10, fill="#111c33", outline="#233554", width=2)

        # Header
        draw.rounded_rectangle([(x, y), (x + w, y + HEADER_H)], radius=10, fill=tbl["header_color"])
        # Cover bottom corners of header
        draw.rectangle([(x, y + HEADER_H - 10), (x + w, y + HEADER_H)], fill=tbl["header_color"])
        draw.line([(x, y + HEADER_H), (x + w, y + HEADER_H)], fill="#3b82f6", width=2)

        draw.text((x + 16, y + 10), tbl["name"], fill="#ffffff", font=font_tbl_header)
        draw.text((x + 16, y + 30), tbl["cat"], fill="#93c5fd", font=font_badge)

        # Rows
        curr_y = y + HEADER_H + 4
        for idx, (col_name, col_type, badge) in enumerate(tbl["cols"]):
            bg_row = "#15223d" if idx % 2 == 0 else "#111c33"
            draw.rectangle([(x + 2, curr_y), (x + w - 2, curr_y + ROW_H)], fill=bg_row)

            # Badge or space
            if badge:
                draw_badge(x + 12, curr_y + 4, badge, badge)
            
            # Column name
            draw.text((x + 46, curr_y + 5), col_name, fill="#f8fafc", font=font_col)

            # Column type
            type_fill = "#38bdf8" if "UUID" in col_type else ("#34d399" if "INT" in col_type else ("#fbbf24" if "TIMESTAMP" in col_type else "#cbd5e1"))
            draw.text((x + w - 140, curr_y + 5), col_type, fill=type_fill, font=font_col)

            curr_y += ROW_H

    # Cardinality relationship helper
    def draw_relation(points, label_start="1", label_end="N", note="CASCADE"):
        line_color = "#38bdf8"
        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]], fill=line_color, width=2)
        
        # Endpoint dots
        draw.ellipse([(points[0][0] - 4, points[0][1] - 4), (points[0][0] + 4, points[0][1] + 4)], fill="#fbbf24", outline="#ffffff", width=1)
        draw.ellipse([(points[-1][0] - 5, points[-1][1] - 5), (points[-1][0] + 5, points[-1][1] + 5)], fill="#38bdf8", outline="#ffffff", width=1)

        # Start label pill
        sx, sy = points[0]
        draw.rounded_rectangle([(sx - 10, sy - 22), (sx + 10, sy - 4)], radius=4, fill="#1e293b", outline="#fbbf24", width=1)
        draw.text((sx - 4, sy - 20), label_start, fill="#fbbf24", font=font_cardinality)

        # End label pill
        ex, ey = points[-1]
        draw.rounded_rectangle([(ex - 10, ey - 22), (ex + 10, ey - 4)], radius=4, fill="#1e293b", outline="#38bdf8", width=1)
        draw.text((ex - 5, ey - 20), label_end, fill="#38bdf8", font=font_cardinality)

        # Midpoint note
        mid_idx = len(points) // 2
        mx = (points[mid_idx - 1][0] + points[mid_idx][0]) // 2
        my = (points[mid_idx - 1][1] + points[mid_idx][1]) // 2
        if note:
            nw = len(note) * 7 + 10
            draw.rounded_rectangle([(mx - nw // 2, my - 10), (mx + nw // 2, my + 10)], radius=4, fill="#0f172a", outline="#475569", width=1)
            draw.text((mx - nw // 2 + 5, my - 7), note, fill="#94a3b8", font=font_badge)

    # Relationship Lines:
    # 1. auth_group -> users_groups (1:N)
    draw_relation([(480, 210), (560, 210)], label_start="1", label_end="N", note="FK group_id")

    # 2. users -> users_groups (1:N)
    draw_relation([(280, 380), (280, 320), (520, 320), (520, 235), (560, 235)], label_start="1", label_end="N", note="FK user_id")

    # 3. users -> events (1:N organizer)
    draw_relation([(480, 520), (560, 520)], label_start="1", label_end="N", note="CASCADE organizer_id")

    # 4. events -> event_posters (1:N)
    draw_relation([(790, 755), (790, 880)], label_start="1", label_end="N", note="CASCADE event_id")

    # 5. events -> tickets (1:N)
    draw_relation([(1020, 520), (1100, 520)], label_start="1", label_end="N", note="CASCADE event_id")

    # 6. tickets -> registrations (1:N)
    draw_relation([(1540, 480), (1620, 480)], label_start="1", label_end="N", note="CASCADE ticket_id")

    # 7. registrations -> payments (1:N)
    draw_relation([(1840, 530), (1840, 660)], label_start="1", label_end="N", note="CASCADE registration_id")

    # 8. users -> registrations (1:N attendee)
    draw_relation([
        (480, 680),
        (520, 680),
        (520, 820),
        (1060, 820),
        (1060, 340),
        (1580, 340),
        (1580, 440),
        (1620, 440)
    ], label_start="1", label_end="N", note="CASCADE user_id")

    # Bottom Legend Panel
    draw.rounded_rectangle([(50, 1260), (WIDTH - 50, 1350)], radius=10, fill="#131d35", outline="#223354", width=2)
    draw.text((70, 1280), "LEGEND & ARCHITECTURE RULES:", fill="#ffffff", font=font_tbl_header)

    draw_badge(360, 1280, "PK", "PK")
    draw.text((395, 1280), "Primary Key (UUID / INT)", fill="#cbd5e1", font=font_legend)

    draw_badge(620, 1280, "FK", "FK")
    draw.text((655, 1280), "Foreign Key (Referential Integrity)", fill="#cbd5e1", font=font_legend)

    draw_badge(950, 1280, "UQ", "UQ")
    draw.text((985, 1280), "Unique Constraint", fill="#cbd5e1", font=font_legend)

    draw.line([(1170, 1290), (1220, 1290)], fill="#38bdf8", width=2)
    draw.ellipse([(1166, 1286), (1174, 1294)], fill="#fbbf24")
    draw.ellipse([(1216, 1286), (1224, 1294)], fill="#38bdf8")
    draw.text((1235, 1280), "1 : N One-to-Many Relationship (with ON DELETE CASCADE)", fill="#cbd5e1", font=font_legend)

    draw.text((1820, 1280), "ADR-0001: Ticket Deletion Cascades to Registrations & Payments", fill="#38bdf8", font=font_legend)

    # Save PNG and JPG
    worktree_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    png_path = os.path.join(worktree_root, "ERD-DicoEvent-versi-1.png")
    jpg_path = os.path.join(worktree_root, "ERD-DicoEvent-versi-1.jpg")

    img.save(png_path, "PNG", optimize=True)
    img.convert("RGB").save(jpg_path, "JPEG", quality=95)
    print(f"Generated: {png_path} ({os.path.getsize(png_path)} bytes)")
    print(f"Generated: {jpg_path} ({os.path.getsize(jpg_path)} bytes)")

if __name__ == "__main__":
    generate_erd()
