"""
数据导出模块

V2.4 新增:
- 导出当前可见区域为图片 (PNG/SVG)
- 导出统计报告 (PDF/HTML)
- 支持 MATLAB 格式 (.mat)
- 支持 HDF5 格式 (.h5)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgGenerator

try:
    import scipy.io as sio
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False


class WaveformExporter:
    """波形数据导出器"""
    
    @staticmethod
    def export_image_png(widget, path: str | Path, width: int = 1920, height: int = 1080) -> bool:
        """
        导出当前可见波形为 PNG 图片
        
        参数:
            widget: WaveformWidget 实例
            path: 保存路径
            width: 图片宽度
            height: 图片高度
        
        返回: 是否成功
        """
        try:
            # 创建图片
            image = QImage(width, height, QImage.Format.Format_ARGB32)
            image.fill(0xFFFFFFFF)  # 白色背景
            
            # 渲染波形
            painter = QPainter(image)
            widget.render(painter)
            painter.end()
            
            # 保存
            return image.save(str(path), "PNG")
        except Exception as e:
            print(f"导出 PNG 失败: {e}")
            return False
    
    @staticmethod
    def export_image_svg(widget, path: str | Path, width: int = 1920, height: int = 1080) -> bool:
        """
        导出当前可见波形为 SVG 矢量图
        
        参数:
            widget: WaveformWidget 实例
            path: 保存路径
            width: 图片宽度
            height: 图片高度
        
        返回: 是否成功
        """
        try:
            generator = QSvgGenerator()
            generator.setFileName(str(path))
            generator.setSize(widget.size())
            generator.setViewBox(widget.rect())
            generator.setTitle("ADC Waveform")
            generator.setDescription(f"Exported on {datetime.now().isoformat()}")
            
            painter = QPainter(generator)
            widget.render(painter)
            painter.end()
            
            return True
        except Exception as e:
            print(f"导出 SVG 失败: {e}")
            return False
    
    @staticmethod
    def export_matlab(
        samples: np.ndarray,
        path: str | Path,
        sample_rate_hz: int,
        metadata: dict[str, Any] | None = None
    ) -> bool:
        """
        导出为 MATLAB .mat 格式
        
        参数:
            samples: 采样数据数组
            path: 保存路径
            sample_rate_hz: 采样率
            metadata: 额外的元数据
        
        返回: 是否成功
        """
        if not HAS_SCIPY:
            print("导出 MATLAB 格式需要安装 scipy: pip install scipy")
            return False
        
        try:
            # 准备数据
            time_array = np.arange(len(samples)) / sample_rate_hz
            
            data = {
                'samples': samples,
                'time': time_array,
                'sample_rate_hz': sample_rate_hz,
                'export_time': datetime.now().isoformat(),
            }
            
            # 添加元数据
            if metadata:
                for key, value in metadata.items():
                    if isinstance(value, (int, float, str, np.ndarray)):
                        data[key] = value
            
            # 保存
            sio.savemat(str(path), data)
            return True
        except Exception as e:
            print(f"导出 MATLAB 格式失败: {e}")
            return False
    
    @staticmethod
    def export_hdf5(
        samples: np.ndarray,
        path: str | Path,
        sample_rate_hz: int,
        metadata: dict[str, Any] | None = None,
        compression: bool = True
    ) -> bool:
        """
        导出为 HDF5 格式（高效压缩存储）
        
        参数:
            samples: 采样数据数组
            path: 保存路径
            sample_rate_hz: 采样率
            metadata: 额外的元数据
            compression: 是否启用压缩
        
        返回: 是否成功
        """
        if not HAS_H5PY:
            print("导出 HDF5 格式需要安装 h5py: pip install h5py")
            return False
        
        try:
            with h5py.File(str(path), 'w') as f:
                # 创建数据集
                if compression:
                    f.create_dataset(
                        'samples',
                        data=samples,
                        compression='gzip',
                        compression_opts=9
                    )
                else:
                    f.create_dataset('samples', data=samples)
                
                # 保存元数据
                f.attrs['sample_rate_hz'] = sample_rate_hz
                f.attrs['export_time'] = datetime.now().isoformat()
                f.attrs['total_samples'] = len(samples)
                f.attrs['duration_s'] = len(samples) / sample_rate_hz
                
                if metadata:
                    for key, value in metadata.items():
                        if isinstance(value, (int, float, str, bool)):
                            f.attrs[key] = value
                
                # 创建时间数组（按需计算，节省空间）
                f.attrs['time_info'] = 'Use: time = np.arange(len(samples)) / sample_rate_hz'
            
            return True
        except Exception as e:
            print(f"导出 HDF5 格式失败: {e}")
            return False
    
    @staticmethod
    def load_hdf5(path: str | Path) -> tuple[np.ndarray, int, dict] | None:
        """
        从 HDF5 文件加载数据
        
        返回: (samples, sample_rate_hz, metadata) 或 None
        """
        if not HAS_H5PY:
            print("加载 HDF5 格式需要安装 h5py: pip install h5py")
            return None
        
        try:
            with h5py.File(str(path), 'r') as f:
                samples = f['samples'][:]
                sample_rate_hz = f.attrs['sample_rate_hz']
                
                # 读取所有元数据
                metadata = dict(f.attrs)
                
                return samples, int(sample_rate_hz), metadata
        except Exception as e:
            print(f"加载 HDF5 文件失败: {e}")
            return None
    
    @staticmethod
    def export_statistics_html(
        stats: dict[str, Any],
        path: str | Path,
        waveform_image_path: str | None = None
    ) -> bool:
        """
        导出统计报告为 HTML 格式
        
        参数:
            stats: 统计数据字典
            path: 保存路径
            waveform_image_path: 波形图片路径（可选）
        
        返回: 是否成功
        """
        try:
            html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ADC 波形统计报告</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 32px;
        }}
        .header p {{
            margin: 5px 0 0 0;
            opacity: 0.9;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        .stat-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }}
        .stat-label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .waveform-image {{
            width: 100%;
            border-radius: 5px;
            margin-top: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌊 ADC 波形统计报告</h1>
        <p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
    
    <div class="card">
        <h2>📊 基本统计</h2>
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">采样率</div>
                <div class="stat-value">{stats.get('sample_rate_hz', 0)} Hz</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">总采样点数</div>
                <div class="stat-value">{stats.get('total_samples', 0):,}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">时长</div>
                <div class="stat-value">{stats.get('duration_s', 0):.2f} s</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">平均值</div>
                <div class="stat-value">{stats.get('mean', 0):.2f}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">RMS</div>
                <div class="stat-value">{stats.get('rms', 0):.2f}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">最大值</div>
                <div class="stat-value">{stats.get('max', 0):.2f}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">最小值</div>
                <div class="stat-value">{stats.get('min', 0):.2f}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">峰峰值</div>
                <div class="stat-value">{stats.get('peak_to_peak', 0):.2f}</div>
            </div>
        </div>
    </div>
"""
            
            # 如果有波形图片，添加到报告中
            if waveform_image_path:
                html += f"""
    <div class="card">
        <h2>📈 波形预览</h2>
        <img src="{waveform_image_path}" alt="Waveform" class="waveform-image">
    </div>
"""
            
            # 频域分析（如果有）
            if 'frequency_hz' in stats and 'period_s' in stats:
                html += f"""
    <div class="card">
        <h2>🔄 频域分析</h2>
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">主频率</div>
                <div class="stat-value">{stats.get('frequency_hz', 0):.2f} Hz</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">周期</div>
                <div class="stat-value">{stats.get('period_s', 0):.6f} s</div>
            </div>
        </div>
    </div>
"""
            
            # 数据质量（如果有）
            if 'crc_errors' in stats or 'seq_gaps' in stats:
                html += f"""
    <div class="card">
        <h2>✅ 数据质量</h2>
        <table>
            <tr>
                <th>指标</th>
                <th>数值</th>
            </tr>
            <tr>
                <td>CRC 错误</td>
                <td>{stats.get('crc_errors', 0)}</td>
            </tr>
            <tr>
                <td>序列跳变</td>
                <td>{stats.get('seq_gaps', 0)}</td>
            </tr>
            <tr>
                <td>重同步次数</td>
                <td>{stats.get('resyncs', 0)}</td>
            </tr>
            <tr>
                <td>短帧数</td>
                <td>{stats.get('short_frames', 0)}</td>
            </tr>
        </table>
    </div>
"""
            
            html += """
    <div class="footer">
        <p>本报告由 xgen-waveform-viewer 生成</p>
    </div>
</body>
</html>
"""
            
            Path(path).write_text(html, encoding='utf-8')
            return True
        except Exception as e:
            print(f"导出 HTML 报告失败: {e}")
            return False
    
    @staticmethod
    def export_statistics_json(stats: dict[str, Any], path: str | Path) -> bool:
        """
        导出统计数据为 JSON 格式
        
        参数:
            stats: 统计数据字典
            path: 保存路径
        
        返回: 是否成功
        """
        try:
            # 转换 numpy 类型为 Python 原生类型
            def convert_value(v):
                if isinstance(v, np.ndarray):
                    return v.tolist()
                elif isinstance(v, (np.integer, np.floating)):
                    return float(v)
                return v
            
            json_stats = {k: convert_value(v) for k, v in stats.items()}
            json_stats['export_time'] = datetime.now().isoformat()
            
            Path(path).write_text(
                json.dumps(json_stats, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            return True
        except Exception as e:
            print(f"导出 JSON 失败: {e}")
            return False


class WaveformComparator:
    """波形比较工具"""
    
    @staticmethod
    def compare_waveforms(
        samples1: np.ndarray,
        samples2: np.ndarray,
        sample_rate_hz: int
    ) -> dict[str, Any]:
        """
        比较两个波形的统计特性
        
        返回: 比较结果字典
        """
        result = {
            'waveform1': {
                'samples': len(samples1),
                'mean': float(np.mean(samples1)),
                'std': float(np.std(samples1)),
                'min': float(np.min(samples1)),
                'max': float(np.max(samples1)),
            },
            'waveform2': {
                'samples': len(samples2),
                'mean': float(np.mean(samples2)),
                'std': float(np.std(samples2)),
                'min': float(np.min(samples2)),
                'max': float(np.max(samples2)),
            },
            'difference': {},
        }
        
        # 计算差异
        result['difference']['mean_diff'] = abs(result['waveform1']['mean'] - result['waveform2']['mean'])
        result['difference']['std_diff'] = abs(result['waveform1']['std'] - result['waveform2']['std'])
        
        # 如果长度相同，计算样本差异
        if len(samples1) == len(samples2):
            diff = samples1.astype(float) - samples2.astype(float)
            result['difference']['sample_mse'] = float(np.mean(diff ** 2))
            result['difference']['sample_mae'] = float(np.mean(np.abs(diff)))
            result['difference']['sample_max_diff'] = float(np.max(np.abs(diff)))
            result['difference']['correlation'] = float(np.corrcoef(samples1, samples2)[0, 1])
        
        return result
