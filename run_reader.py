def run_reader(run_file_dir):
    material_names = []
    with open(run_file_dir, 'r', encoding='utf-8') as f:
        lines = [line.strip().replace(' ','').replace('\t', '') for line in f.readlines()]

        material_index = lines.index("[MATERIAL]")
        material_count = int(lines[material_index+1].split('=')[1])
        
        for i in range(material_index+2, material_index+2+material_count):
            material_names.append(lines[i].split('=')[1])

    return material_names
