def calculate_padding(buffer_len, stride):
    return (stride-(buffer_len%stride)) % stride
