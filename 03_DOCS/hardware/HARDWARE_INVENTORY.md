# Inventario de Hardware del Proyecto — INDIVISA INGENIUM 2026

**Fecha de Registro:** 29 de septiembre de 2026  
**Ubicación:** [`03_DOCS/hardware/HARDWARE_INVENTORY.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/03_DOCS/hardware/HARDWARE_INVENTORY.md)  
**Criterio de Validación:** Solo datos verificados experimental, física o diagnósticamente. Todo parámetro no confirmado se registra explícitamente como **UNKNOWN** para cumplir con la Regla 9 y 10 de [`AGENTS.md`](file:///C:/Users/migue/Downloads/SALLE/INDIVISA_INGENIUM_2026/AGENTS.md).

---

## 1. Raspberry Pi 5

- **Modelo:** Raspberry Pi 5 (Revisión exacta de placa física: **UNKNOWN**)
- **RAM:** **UNKNOWN** *(Existen variantes de 2 GB, 4 GB, 8 GB y 16 GB; pendiente de verificación física o comando `free -m` / `/proc/meminfo` al bootear la placa)*
- **Sistema Operativo:** **UNKNOWN** *(Pendiente de confirmación de la imagen grabada en el medio de arranque; se proyecta Raspberry Pi OS de 64 bits)*
- **Arquitectura:** ARM64 / aarch64 (Broadcom BCM2712, Quad-core ARM Cortex-A76 @ 2.4 GHz)
- **Almacenamiento:** **UNKNOWN** *(Tipo, fabricante y capacidad de la tarjeta MicroSD o unidad SSD NVMe no verificados en el componente físico)*
- **Alimentación:** **UNKNOWN** *(Especificación nominal recomendada de plataforma: 5V / 5A USB-C PD; cargador o fuente física real disponible en mesa: UNKNOWN)*
- **Refrigeración:** **UNKNOWN** *(Presencia de disipador pasivo, Active Cooler oficial o disipador de terceros en la unidad física: UNKNOWN)*
- **Conectividad:** **UNKNOWN** *(La plataforma base integra Wi-Fi 802.11ac dual-band, Bluetooth 5.0 / BLE y Gigabit Ethernet; estado de activación y configuración IP local: UNKNOWN)*

---

## 2. ESP32-CAM

- **Fabricante:** **UNKNOWN** *(Pendiente de inspección de la serigrafía en la PCB física; comúnmente fabricado por AI-Thinker u otros ensambladores)*
- **Modelo Exacto:** **UNKNOWN** *(Pendiente de lectura directa de la serigrafía de la placa)*
- **Microcontrolador:** ESP32 (SoC Xtensa Dual-Core 32-bit LX6; revisión de silicio exacta: **UNKNOWN**)
- **Sensor de Cámara:** **UNKNOWN** *(Generalmente suministrado con módulo sensor OV2640, pero existen variantes con OV7670 o lentes gran angular; modelo físico real no verificado)*
- **PSRAM:** **UNKNOWN** *(Capacidad real del chip de memoria pseudoestática externa no verificada por diagnóstico de arranque: UNKNOWN)*
- **Método de Programación:** **UNKNOWN** *(Uso de programador externo USB-UART FTDI/CH340 o shield ESP32-CAM-MB micro-USB: UNKNOWN)*
- **Alimentación:** **UNKNOWN** *(Voltaje y fuente de poder física real a utilizar en el banco de trabajo: UNKNOWN)*
- **Pinout:** **UNKNOWN** *(El pinout depende de la variante de hardware comprobada; prohibido asumir asignación de pines hasta cotejar físicamente con serigrafía y multímetro)*

---

## 3. Dispositivo de Sensores (Instrumentación Mecatrónica)

- **Microcontrolador:** **UNKNOWN** *(No determinado ni comprobado si se empleará un microcontrolador secundario dedicado tipo ESP32 / Arduino Nano / RP2040, o conexión directa vía ADC/I2C al Raspberry Pi 5)*
- **Sensor IMU:** **UNKNOWN** *(Modelo exacto de la unidad de medición inercial no comprobado físicamente: MPU6050, LSM6DS3, MPU9250 u otro: UNKNOWN)*
- **Comunicación:** **UNKNOWN** *(Protocolo físico de transmisión entre el bloque de sensores y el nodo de procesamiento: I2C, SPI, UART o bus analógico: UNKNOWN)*
- **Alimentación:** **UNKNOWN** *(Nivel de tensión de operación de los sensores: 3.3V vs 5V: UNKNOWN)*
- **Montaje:** **UNKNOWN** *(Mecanismo físico de acoplamiento ergonómico en mano/guante/muñeca o soporte estructural: UNKNOWN)*

---

## 4. Laptop (Estación de Desarrollo y Visualización Desacoplada)

*Datos obtenidos mediante consulta diagnóstica directa del sistema local (CIM / WMI):*

- **Fabricante y Modelo:** ASUSTeK COMPUTER INC. — Vivobook_ASUSLaptop X1404ZA_F1404ZA
- **Sistema Operativo:** Microsoft Windows 11 Home Single Language (Versión 10.0.26200, 64-bit)
- **CPU:** 12th Gen Intel(R) Core(TM) i5-1235U (10 núcleos físicos: 2 núcleos de alto rendimiento P-core + 8 núcleos de eficiencia E-core; 12 procesadores lógicos; frecuencia base 1.30 GHz, turbo hasta 4.40 GHz)
- **RAM:** 24 GB DDR4 (24,852,024 KB memoria física visible; 11,240,064 KB memoria física disponible actualmente)
- **GPU:** Intel(R) Iris(R) Xe Graphics
- **USB:** Controlador de host eXtensible Intel(R) USB 3.10 - 1.20 (Microsoft) con puertos compatibles USB 3.1 Gen 1 / USB 2.0
- **Wi-Fi:** Intel(R) Wireless-AC 9560 160MHz (Soporte IEEE 802.11a/b/g/n/ac, doble banda 2.4 GHz y 5 GHz)

---

## 5. Teclado

*Dispositivos de entrada identificados en el sistema anfitrión:*

- **Tipo:** 
  1. Teclado integrado de computadora portátil (Laptop Keyboard).
  2. Teclado externo periférico (Kit inalámbrico USB / HID).
- **Conexión:**
  - Teclado integrado: Bus interno ACPI / I2C / ATK integrado en el chasis del portátil.
  - Teclado externo: Conexión USB a través de nano-receptor RF inalámbrico (Dispositivo Compuesto USB).
- **Identificación en Linux/Windows:**
  - **En Windows (Sistema actual):**
    - Teclado integrado: `HID\ASUP1411&COL04\5&33C65996&0&0003` / `ACPI\ATK3001\4&2716765D&0` (*Nombre descriptivo:* "ASUS Keyboard" / "Teclado PS/2 extendido para PC/AT").
    - Teclado externo: `HID\VID_3151&PID_3020&MI_00\7&38E75F89&0&0000` (*Dispositivo compuesto USB Vendor ID 0x3151, Product ID 0x3020*).
  - **En Linux (Cuando se conecte a la Raspberry Pi 5):**
    - Teclado externo USB: **UNKNOWN** hasta realizar enumeración física mediante `lsusb` / `dmesg` en la RPi 5 *(se espera reporte como dispositivo HID `3151:3020`)*.
    - Teclado integrado: **No aplica** *(periférico integrado exclusivo del chasis de la laptop ASUS)*.

---

## 6. Estado de Verificación de Hardware y Próximos Pasos

```text
+-----------------------+---------------------+---------------------------------------------+
| DISPOSITIVO           | ESTADO ACTUAL       | ACCIÓN REQUERIDA PARA COMPLETAR INVENTARIO  |
+-----------------------+---------------------+---------------------------------------------+
| Raspberry Pi 5        | PENDIENTE ARRANQUE  | Encender y ejecutar 'cat /proc/cpuinfo',    |
|                       |                     | 'free -m', 'cat /etc/os-release', 'vcgencmd'|
| ESP32-CAM             | PENDIENTE INSPECCIÓN| Revisar serigrafía de placa y sensor OV2640;|
|                       |                     | verificar modelo exacto de programador      |
| Dispositivo Sensores  | PENDIENTE SELECCIÓN | Inspeccionar componentes sueltos en mesa:   |
|                       |                     | verificar modelo de IMU/flex y microcontrol |
| Laptop ASUS           | 100% VERIFICADO     | Listo para ejecutar frontend desacoplado    |
| Teclado               | 100% VERIFICADO     | Listo para interacción y control            |
+-----------------------+---------------------+---------------------------------------------+
```

---

## 7. PENDING HARDWARE VERIFICATION

La siguiente lista contiene los elementos que permanecen como **UNKNOWN** y que están estrictamente prohibidos de inventar o simular como hardware comprobado:

1. **ESP32-CAM:**
   - [ ] Fabricante y revisión exacta de serigrafía de la placa (AI-Thinker vs clon).
   - [ ] Modelo exacto del sensor óptico (OV2640, OV7670 o lente gran angular).
   - [ ] Presencia y capacidad del chip PSRAM externo (ESP32-CAM sin PSRAM se limita a QVGA).
   - [ ] Pinout de asignación de cámara y bus de control (prohibido asumir pinout sin inspección física).
   - [ ] Dirección IP asignada en la red local de prueba (configurable mediante `settings.json`, no hardcodeada).

2. **Instrumentación Mecatrónica (Sensores):**
   - [ ] Modelo de la Unidad de Medición Inercial (IMU): MPU6050, LSM6DS3, MPU9250 u otro (**UNKNOWN**).
   - [ ] Dirección I2C del sensor inercial (**UNKNOWN**; por ejemplo, 0x68 o 0x69 según pin AD0).
   - [ ] Pines GPIO y bus físico de enlace con Raspberry Pi 5 (**UNKNOWN**).
   - [ ] Tecnología de sensores de flexión (galgas extensométricas resistivas, hilo resistivo o sensores ópticos flex).
   - [ ] Microcontrolador secundario dedicado para adquisición (si aplica: RP2040, Arduino Nano, ESP32 o ADC directo).

3. **Raspberry Pi 5:**
   - [ ] Memoria RAM física (2 GB, 4 GB, 8 GB o 16 GB).
   - [ ] Medio de almacenamiento de arranque (MicroSD clase A2 vs SSD NVMe M.2).
   - [ ] Sistema de refrigeración instalado (Active Cooler oficial vs pasivo).
