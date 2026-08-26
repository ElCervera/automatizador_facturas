import logging

def get_logger(name: str) -> logging.Logger:
    """
    Retorna un logger simple para consola y archivo.
    Niveles: info, warning, error.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Handler para archivo en debug/robo_facturador.log
        try:
            from config.settings import DEBUG_DIR
            file_path = DEBUG_DIR / "robo_facturador.log"
            file_handler = logging.FileHandler(file_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass
            
        logger.propagate = False
    return logger
