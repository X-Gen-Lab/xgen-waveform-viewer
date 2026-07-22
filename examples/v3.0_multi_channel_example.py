"""
V3.0 多通道示例

演示如何使用多通道功能：
- 创建和配置多个通道
- 模拟多通道数据采集
- 通道分组和管理
- 通道配置保存和加载
"""

import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer

# 添加项目路径（如果需要）
sys.path.insert(0, '../src')

from xgen_waveform_viewer.multi_channel import MultiChannelManager
from xgen_waveform_viewer.channel_panel import ChannelPanel


class MultiChannelDemo(QMainWindow):
    """多通道演示窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("V3.0 多通道演示")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建多通道管理器
        self.manager = MultiChannelManager()
        
        # 设置 UI
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # 添加通道管理面板
        self.channel_panel = ChannelPanel(self.manager)
        layout.addWidget(self.channel_panel)
        
        # 初始化通道
        self._setup_channels()
        
        # 启动数据模拟
        self._setup_data_simulation()
    
    def _setup_channels(self):
        """设置演示通道"""
        # 定义通道配置
        channels = [
            {
                "id": 0,
                "label": "温度传感器",
                "color": "#ff0000",
                "group": "环境监测",
                "base_value": 2048,
                "amplitude": 200,
            },
            {
                "id": 1,
                "label": "湿度传感器",
                "color": "#0000ff",
                "group": "环境监测",
                "base_value": 2500,
                "amplitude": 300,
            },
            {
                "id": 2,
                "label": "光照传感器",
                "color": "#00ff00",
                "group": "环境监测",
                "base_value": 1500,
                "amplitude": 500,
            },
            {
                "id": 3,
                "label": "压力传感器",
                "color": "#ffff00",
                "group": "压力监测",
                "base_value": 3000,
                "amplitude": 400,
            },
        ]
        
        # 添加通道
        for ch in channels:
            self.manager.add_channel(
                channel_id=ch["id"],
                label=ch["label"],
                color=ch["color"]
            )
            self.manager.update_channel_config(ch["id"], group=ch["group"])
        
        # 保存配置供后续参考
        self.channel_configs = channels
        
        print("✓ 已创建 4 个演示通道")
    
    def _setup_data_simulation(self):
        """设置数据模拟定时器"""
        self.seq_number = 0
        self.time_elapsed = 0.0
        
        # 每 50ms 生成一批数据
        self.timer = QTimer()
        self.timer.timeout.connect(self._generate_data)
        self.timer.start(50)
        
        print("✓ 数据模拟已启动")
    
    def _generate_data(self):
        """生成模拟数据"""
        # 为每个通道生成不同的波形
        for ch_config in self.channel_configs:
            ch_id = ch_config["id"]
            base = ch_config["base_value"]
            amp = ch_config["amplitude"]
            
            # 生成 128 个采样点
            samples_count = 128
            t = np.arange(samples_count) * 0.0001 + self.time_elapsed
            
            # 根据通道 ID 使用不同的波形
            if ch_id == 0:
                # 正弦波 + 噪声
                signal = base + amp * np.sin(2 * np.pi * 1.0 * t)
                noise = np.random.normal(0, 10, samples_count)
                samples = (signal + noise).astype(np.uint16)
            
            elif ch_id == 1:
                # 方波
                signal = base + amp * np.sign(np.sin(2 * np.pi * 0.5 * t))
                noise = np.random.normal(0, 20, samples_count)
                samples = (signal + noise).astype(np.uint16)
            
            elif ch_id == 2:
                # 锯齿波
                signal = base + amp * (2 * (t % 1.0) - 1)
                noise = np.random.normal(0, 15, samples_count)
                samples = (signal + noise).astype(np.uint16)
            
            else:
                # 随机漂移
                signal = base + amp * np.cumsum(np.random.randn(samples_count)) * 0.1
                samples = np.clip(signal, 0, 4095).astype(np.uint16)
            
            # 添加数据到通道
            self.manager.append_data(
                channel_id=ch_id,
                samples=samples,
                seq=self.seq_number,
                timestamp=self.time_elapsed
            )
        
        self.seq_number += 1
        self.time_elapsed += 0.0128  # 128 samples @ 10kHz


def main():
    """主函数"""
    print("=" * 60)
    print("xgen-waveform-viewer V3.0 - 多通道演示")
    print("=" * 60)
    print()
    
    app = QApplication(sys.argv)
    
    # 创建演示窗口
    demo = MultiChannelDemo()
    demo.show()
    
    print()
    print("演示说明：")
    print("1. 查看右侧通道管理面板")
    print("2. 尝试修改通道标签和颜色")
    print("3. 切换通道可见性")
    print("4. 修改通道分组")
    print("5. 观察不同通道的波形特征")
    print()
    print("提示：配置会自动保存")
    print()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
