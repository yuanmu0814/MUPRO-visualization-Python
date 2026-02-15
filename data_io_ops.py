import math

from color_utils import get_rgb


def load_data(view, file_path: str) -> int:
    view.updateFlag = False
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    if len(lines) < 2:
        return 0
    line1 = lines[0].strip()
    line2 = lines[1].strip()
    count1 = len(line1.split())
    count2 = len(line2.split())

    x = y = z = 0
    if count1 != count2:
        parts = line1.split()
        if len(parts) >= 3:
            x, y, z = map(int, parts[:3])
        data_lines = lines[1:]
    else:
        last_line = lines[-1].strip()
        parts = last_line.split()
        if len(parts) >= 3:
            x, y, z = map(int, parts[:3])
        data_lines = lines

    column_number = count2 - 3
    row_number = x * y * z
    view.vtk_data = []
    for line in data_lines[:row_number]:
        parts = line.split()
        if len(parts) < 3 + column_number:
            continue
        row = [float(value) for value in parts[3 : 3 + column_number]]
        view.vtk_data.append(row)

    view.tempX = x
    view.tempY = y
    view.tempZ = z
    view.updateExtraction(x, y, z)
    return column_number


def update_extraction(view, x: int, y: int, z: int) -> None:
    if view.xmaxAll < x - 1:
        view.xmaxAll = x - 1
    if view.ymaxAll < y - 1:
        view.ymaxAll = y - 1
    if view.zmaxAll < z - 1:
        view.zmaxAll = z - 1
    view.xminAll = 0
    view.yminAll = 0
    view.zminAll = 0
    view.xmax = x - 1
    view.ymax = y - 1
    view.zmax = z - 1
    view.xmin = 0
    view.ymin = 0
    view.zmin = 0

    view.xmin_LE.setText(str(view.xminAll + 1))
    view.ymin_LE.setText(str(view.yminAll + 1))
    view.zmin_LE.setText(str(view.zminAll + 1))
    view.xmax_LE.setText(str(view.xmaxAll + 1))
    view.ymax_LE.setText(str(view.ymaxAll + 1))
    view.zmax_LE.setText(str(view.zmaxAll + 1))

    total_points = (
        (view.xmaxAll - view.xminAll + 1)
        * (view.ymaxAll - view.yminAll + 1)
        * (view.zmaxAll - view.zminAll + 1)
    )
    interval = 1
    if view.xminAll != view.xmaxAll and view.yminAll != view.ymaxAll and view.zminAll != view.zmaxAll:
        if total_points > 1000000:
            interval = math.ceil((total_points / 1000000.0) ** (1 / 3.0))
    else:
        if total_points > 1000000:
            interval = math.ceil((total_points / 1000000.0) ** (1 / 2.0))
    view.xDelta_LE.setText(str(interval))
    view.yDelta_LE.setText(str(interval))
    view.zDelta_LE.setText(str(interval))


def output_scalar(view, path: str, column_number: int, x: int, y: int, z: int) -> None:
    if view.data2Dx:
        x += 2
    else:
        x += 1
    if view.data2Dy:
        y += 2
    else:
        y += 1
    if view.data2Dz:
        z += 2
    else:
        z += 1
    row_number = x * y * z
    out_path = f"{path}.{column_number+1}.vtk"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("Structured Points\n")
        f.write("ASCII\n\n")
        f.write("DATASET STRUCTURED_POINTS\n")
        f.write(f"DIMENSIONS {x} {y} {z}\n")
        f.write("ORIGIN 0 0 0\n")
        f.write(
            f"SPACING {view.rescaleX_LE.text()} {view.rescaleY_LE.text()} {view.rescaleZ_LE.text()}\n\n"
        )
        f.write(f"POINT_DATA {row_number}\n")
        f.write("SCALARS scalar float\n")
        f.write("LOOKUP_TABLE default\n")
        for m in range(z):
            for n in range(y):
                for w in range(x):
                    if view.data2Dx or view.data2Dy or view.data2Dz:
                        if view.data2Dx:
                            value = view.vtk_data[n * z + m][column_number]
                        elif view.data2Dy:
                            value = view.vtk_data[w * (y - 1) * z + m][column_number]
                        else:
                            value = view.vtk_data[w * y * (z - 1) + n * (z - 1)][column_number]
                    else:
                        value = view.vtk_data[w * y * z + n * z + m][column_number]
                    f.write(f"{value:14.6e}\n")
    view.scalarName = out_path


def output_vector(view, path: str, col_x: int, col_y: int, col_z: int, x: int, y: int, z: int) -> None:
    x += 1
    y += 1
    z += 1
    row_number = x * y * z
    out_path = f"{path}.{col_x+1}{col_y+1}{col_z+1}.vtk"
    magnitude = [0.0] * row_number
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("Structured Points\n")
        f.write("ASCII\n\n")
        f.write("DATASET STRUCTURED_POINTS\n")
        f.write(f"DIMENSIONS {x} {y} {z}\n")
        f.write("ORIGIN 0 0 0\n")
        f.write(
            f"SPACING {view.rescaleX_LE.text()} {view.rescaleY_LE.text()} {view.rescaleZ_LE.text()}\n\n"
        )
        f.write(f"POINT_DATA {row_number}\n")
        f.write("SCALARS Magnitude float \n")
        f.write("LOOKUP_TABLE default \n")
        for m in range(z):
            for n in range(y):
                for w in range(x):
                    idx = w * y * z + n * z + m
                    value = math.sqrt(
                        view.vtk_data[idx][col_x] ** 2
                        + view.vtk_data[idx][col_y] ** 2
                        + view.vtk_data[idx][col_z] ** 2
                    )
                    f.write(f"{value:14.6e}\n")
        f.write("\n")
        f.write("VECTORS vector float\n")
        for m in range(z):
            for n in range(y):
                for w in range(x):
                    idx = w * y * z + n * z + m
                    vx = view.vtk_data[idx][col_x]
                    vy = view.vtk_data[idx][col_y]
                    vz = view.vtk_data[idx][col_z]
                    f.write(f"{vx:14.6e} {vy:14.6e} {vz:14.6e}\n")
                    magnitude[idx] = math.sqrt(vx * vx + vy * vy + vz * vz)
        magnitude_range = [0.0, max(magnitude) if magnitude else 1.0]
        z_range = [-magnitude_range[1], magnitude_range[1]]

        f.write("\n")
        f.write("VECTORS RGB unsigned_char\n")
        for m in range(z):
            for n in range(y):
                for w in range(x):
                    idx = w * y * z + n * z + m
                    rgb = get_rgb(
                        view.vtk_data[idx][col_x],
                        view.vtk_data[idx][col_y],
                        view.vtk_data[idx][col_z],
                        magnitude_range,
                        z_range,
                    )
                    f.write(f"{rgb[0]:.0f} {rgb[1]:.0f} {rgb[2]:.0f}\n")
    view.vectorName = out_path
