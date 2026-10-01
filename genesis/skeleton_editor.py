"""Built-in, CPU-only skeleton editor for the GENESIS Pose Library."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QSaveFile, QIODevice, QUrl, QProcess, QProcessEnvironment, QTimer, pyqtSlot
from PyQt6.QtGui import QColor, QImage, QImageReader, QPainter, QPen, QShortcut, QKeySequence
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFileDialog,
    QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget)
from genesis.pose_document import (PARTS, BODY18, BODY25, HAND, add_hands,
    merged_document, new_document, standing_person, validate_document)

COLORS = ["#ff4040","#ff9000","#ffe000","#80ee00","#00db50","#00dcbe",
          "#00bbff","#0070ff","#6040ff","#c000ff","#ff00c0","#ff4080"]


def local_path(value):
    url = QUrl(value)
    if url.isLocalFile():
        return Path(url.toLocalFile())
    if url.scheme():
        raise ValueError("Only local files can be opened.")
    return Path(value).expanduser()


def atomic_write(path, data):
    writer = QSaveFile(str(path))
    if not writer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(writer.errorString())
    if writer.write(data) != len(data):
        writer.cancelWriting()
        raise OSError(writer.errorString())
    if not writer.commit():
        raise OSError(writer.errorString())


def read_document(path, dimensions=None):
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Pose JSON exceeds the 8 MB limit.")
    return validate_document(json.loads(path.read_text(encoding="utf-8")), dimensions)


class PoseCanvas(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.drag = None
        self.zoom = 1.0
        self.pan = QPointF()
        self.pan_start = None
        self.setMinimumSize(360,360)
        self.setMouseTracking(True)
        self.setAccessibleName("Skeleton canvas: drag a joint or move a person")

    def transform(self):
        d = self.editor.document
        scale = self.zoom * min(self.width()/d["canvas_width"], self.height()/d["canvas_height"])
        return scale, (self.width()-d["canvas_width"]*scale)/2+self.pan.x(), (self.height()-d["canvas_height"]*scale)/2+self.pan.y()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#191c21"))
        scale,x,y = self.transform()
        p.translate(x,y)
        p.scale(scale,scale)
        self.draw(p, True, scale)
        p.end()

    def draw(self, p, editing=False, scale=1):
        e, d = self.editor, self.editor.document
        bounds = QRectF(0,0,d["canvas_width"],d["canvas_height"])
        p.save()
        p.setClipRect(bounds)
        p.fillRect(bounds,QColor("black"))
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if editing and not e.reference.isNull() and e.show_reference.isChecked():
            p.setOpacity(.32)
            p.drawImage(bounds,e.reference)
            p.setOpacity(1)
        for person_index, person in enumerate(d["people"]):
            for part_index,key in enumerate(PARTS):
                pts = person[key]
                edges = (BODY25 if len(pts)==75 else BODY18) if part_index==0 else (HAND if part_index in (1,2) else [])
                for j,(a,b) in enumerate(edges):
                    if max(a,b)*3+2>=len(pts) or pts[a*3+2]<=0 or pts[b*3+2]<=0:
                        continue
                    color = QColor(COLORS[j%len(COLORS)])
                    p.setPen(QPen(color,3 if part_index==0 else 1.4))
                    p.drawLine(QPointF(*pts[a*3:a*3+2]),QPointF(*pts[b*3:b*3+2]))
                for i in range(0,len(pts),3):
                    if pts[i+2]<=0:
                        continue
                    active = editing and person_index==e.person.currentIndex() and part_index==e.part.currentIndex()
                    p.setPen(QPen(QColor("#ffffff" if active else COLORS[(i//3)%len(COLORS)]),1/scale if editing else 1))
                    p.setBrush(QColor(COLORS[(i//3)%len(COLORS)]))
                    radius = (4.5/scale if active else 2.5) if editing else (3 if part_index==0 else 1.5)
                    p.drawEllipse(QPointF(pts[i],pts[i+1]),radius,radius)
        p.restore()

    def point(self,event):
        scale,x,y = self.transform()
        return ((event.position().x()-x)/scale,(event.position().y()-y)/scale)

    def fit(self):
        self.zoom=1.0
        self.pan=QPointF()
        self.update()

    def wheelEvent(self,event):
        x,y=self.point(event)
        self.zoom=max(1.0,min(8.0,self.zoom*(1.2 if event.angleDelta().y()>0 else 1/1.2)))
        scale,ox,oy=self.transform()
        self.pan+=QPointF(event.position().x()-ox-x*scale,event.position().y()-oy-y*scale)
        if self.zoom==1.0:self.pan=QPointF()
        self.update()
        event.accept()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:
            self.pan_start=(event.position(),QPointF(self.pan))
            return
        if event.button()!=Qt.MouseButton.LeftButton:
            return
        e = self.editor
        x,y = self.point(event)
        scale,_,_ = self.transform()
        best, distance = None, (12/scale)**2
        key = PARTS[e.part.currentIndex()]
        for n,person in enumerate(e.document["people"]):
            pts = person[key]
            for i in range(0,len(pts),3):
                delta = (pts[i]-x)**2+(pts[i+1]-y)**2
                if pts[i+2]>0 and delta<distance:
                    best,distance = (n,i),delta
        if best is None:
            return
        e.person.setCurrentIndex(best[0])
        self.drag = (best[0],key,best[1],x,y,deepcopy(e.document))
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self,event):
        if self.pan_start is not None:
            self.pan=self.pan_start[1]+event.position()-self.pan_start[0]
            self.update()
            return
        if self.drag is None:
            return
        n,key,i,start_x,start_y,original = self.drag
        e = self.editor
        x,y = self.point(event)
        d = deepcopy(original)
        person = d["people"][n]
        w,h = d["canvas_width"],d["canvas_height"]
        if e.move_person.isChecked():
            visible = [(pts[j],pts[j+1]) for name in PARTS for pts in [person[name]]
                       for j in range(0,len(pts),3) if pts[j+2]>0]
            dx,dy = x-start_x,y-start_y
            if visible:
                dx = max(-min(a for a,b in visible), min(dx,w-max(a for a,b in visible)))
                dy = max(-min(b for a,b in visible), min(dy,h-max(b for a,b in visible)))
            for name in PARTS:
                pts=person[name]
                for j in range(0,len(pts),3):
                    if pts[j+2]>0:
                        pts[j]+=dx
                        pts[j+1]+=dy
        else:
            person[key][i:i+3] = [max(0,min(w,x)),max(0,min(h,y)),1.0]
        e.document=d
        self.update()

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:
            self.pan_start=None
            return
        if self.drag is not None:
            before = self.drag[-1]
            if before != self.editor.document:
                self.editor.remember(before)
            self.drag=None
            self.unsetCursor()


class SkeletonEditor(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GENESIS · Skeleton Editor")
        self.resize(1040,820)
        self.setMinimumSize(790,620)
        self.document=new_document()
        self.saved=deepcopy(self.document)
        self.undo_stack=[]
        self.redo_stack=[]
        self.path=None
        self.reference=QImage()
        self.reference_path=None
        self.extractor=None
        self.extract_timer=QTimer(self)
        self.extract_timer.setSingleShot(True)
        self.extract_timer.timeout.connect(self.cancel_extraction)
        self.cancelled=False
        self.setStyleSheet("QDialog { background:#101215; color:#f4efe6; } "
            "QLabel,QCheckBox { color:#e6ded0; } QPushButton,QComboBox { "
            "background:#23272d; color:#e6c17c; padding:7px; border:1px solid #555047; } "
            "QPushButton:disabled { color:#777; }")
        layout=QVBoxLayout(self)
        toolbar=QHBoxLayout()
        layout.addLayout(toolbar)
        for text,fn in [("New",self.new),("Import JSON",lambda:self.import_json(False)),
                        ("Merge JSON",lambda:self.import_json(True)),("Save JSON",self.save),
                        ("Export PNG",self.export_png)]:
            button=QPushButton(text)
            button.clicked.connect(lambda checked=False, action=fn:action())
            toolbar.addWidget(button)
        self.undo_button=QPushButton("Undo")
        self.redo_button=QPushButton("Redo")
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)
        toolbar.addWidget(self.undo_button)
        toolbar.addWidget(self.redo_button)
        tools=QHBoxLayout()
        layout.addLayout(tools)
        self.person=QComboBox()
        self.part=QComboBox()
        self.part.addItems(["Body","Left hand","Right hand","Face"])
        tools.addWidget(QLabel("Person"))
        tools.addWidget(self.person)
        tools.addWidget(self.part)
        for text,fn in [("Add person",self.add_person),("Remove person",self.remove_person),
                        ("Add hands",self.make_hands)]:
            button=QPushButton(text)
            button.clicked.connect(lambda checked=False, action=fn:action())
            tools.addWidget(button)
        self.move_person=QCheckBox("Move whole person")
        tools.addWidget(self.move_person)
        self.canvas=PoseCanvas(self)
        layout.addWidget(self.canvas,1)
        self.person.currentIndexChanged.connect(self.canvas.update)
        self.part.currentIndexChanged.connect(self.canvas.update)
        reference_row=QHBoxLayout()
        layout.addLayout(reference_row)
        reference_button=QPushButton("Load reference image")
        reference_button.clicked.connect(self.choose_reference)
        reference_row.addWidget(reference_button)
        self.extract_button=QPushButton("Extract joints (CPU)")
        self.extract_button.setEnabled(False)
        self.extract_button.clicked.connect(self.extract_cpu)
        reference_row.addWidget(self.extract_button)
        self.cancel_button=QPushButton("Cancel extraction")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_extraction)
        reference_row.addWidget(self.cancel_button)
        fit_button=QPushButton("Fit view")
        fit_button.clicked.connect(self.canvas.fit)
        reference_row.addWidget(fit_button)
        self.show_reference=QCheckBox("Show reference overlay")
        self.show_reference.setChecked(True)
        self.show_reference.toggled.connect(self.canvas.update)
        reference_row.addWidget(self.show_reference)
        self.status=QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        hint=QLabel("Drag a visible joint. Choose a hand to edit its fingers. "
                   "Wheel: zoom. Middle drag: pan. PNG export contains only joints and bones; images are reference overlays.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        for key,fn in [("Ctrl+Z",self.undo),("Ctrl+Shift+Z",self.redo),("Ctrl+S",self.save)]:
            QShortcut(QKeySequence(key),self,activated=fn)
        self.refresh()

    def refresh(self):
        selected=self.person.currentIndex()
        self.person.blockSignals(True)
        self.person.clear()
        self.person.addItems(["Person "+str(i+1) for i in range(len(self.document["people"]))])
        self.person.setCurrentIndex(max(0,min(selected,self.person.count()-1)))
        self.person.blockSignals(False)
        self.undo_button.setEnabled(bool(self.undo_stack))
        self.redo_button.setEnabled(bool(self.redo_stack))
        dirty=self.document!=self.saved
        label=str(self.path) if self.path else "New pose"
        self.status.setText(f"{label} · {self.document['canvas_width']} × {self.document['canvas_height']}"
                            + (" · Unsaved changes" if dirty else ""))
        self.setWindowTitle("GENESIS · Skeleton Editor"+(" *" if dirty else ""))
        self.canvas.update()

    def remember(self,before):
        self.undo_stack.append(deepcopy(before))
        self.undo_stack=self.undo_stack[-50:]
        self.redo_stack.clear()
        self.refresh()

    def change(self,document):
        before=self.document
        self.document=validate_document(document)
        if before!=self.document:
            self.remember(before)

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(deepcopy(self.document))
            self.document=self.undo_stack.pop()
            self.refresh()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(deepcopy(self.document))
            self.document=self.redo_stack.pop()
            self.refresh()

    def confirm_close(self):
        if self.extractor is not None and self.extractor.state()!=QProcess.ProcessState.NotRunning:
            self.cancel_extraction()
        if self.document==self.saved:
            return True
        answer=QMessageBox.question(self,"Unsaved skeleton","Save your edited skeleton before continuing?",
            QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
        if answer==QMessageBox.StandardButton.Save:
            return self.save()
        if answer==QMessageBox.StandardButton.Discard:
            self.document=deepcopy(self.saved)
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.refresh()
            return True
        return False

    def closeEvent(self,event):
        if self.confirm_close(): event.accept()
        else: event.ignore()

    def reject(self):
        if self.confirm_close(): super().reject()

    def new(self):
        if not self.confirm_close(): return
        width,ok=QInputDialog.getInt(self,"New skeleton","Canvas width",768,16,8192)
        if not ok:return
        height,ok=QInputDialog.getInt(self,"New skeleton","Canvas height",1024,16,8192)
        if not ok:return
        self.document=new_document(width,height)
        self.saved=deepcopy(self.document)
        self.path=None
        self.reference=QImage()
        self.reference_path=None
        self.extract_button.setEnabled(False)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.canvas.fit()
        self.refresh()

    def error(self,exc):
        QMessageBox.warning(self,"Skeleton editor",str(exc))

    def load(self,path,merge=False):
        try:
            if path.stat().st_size>8*1024*1024:
                raise ValueError("Pose JSON exceeds the 8 MB limit.")
            raw=json.loads(path.read_text(encoding="utf-8"))
            frame=raw[0] if isinstance(raw,list) and len(raw)==1 else raw
            dimensions=None
            if isinstance(frame,dict) and ("canvas_width" not in frame or "canvas_height" not in frame):
                width,ok=QInputDialog.getInt(self,"Source canvas","Original image width (pixels)",768,16,8192)
                if not ok:return False
                height,ok=QInputDialog.getInt(self,"Source canvas","Original image height (pixels)",1024,16,8192)
                if not ok:return False
                dimensions=(width,height)
            document=validate_document(raw,dimensions)
            if merge:
                self.change(merged_document(self.document,document))
            else:
                if not self.confirm_close():return False
                self.document=document
                self.saved=deepcopy(document)
                self.path=path
                self.reference=QImage()
                self.reference_path=None
                self.extract_button.setEnabled(False)
                self.undo_stack.clear()
                self.redo_stack.clear()
                self.canvas.fit()
                self.refresh()
            return True
        except (OSError,ValueError,TypeError) as exc:
            self.error(exc)
            return False

    def import_json(self,merge=False):
        filename,_=QFileDialog.getOpenFileName(self,"Merge pose JSON" if merge else "Import pose JSON",
                                              str(self.path.parent) if self.path else str(Path.home()),"Pose JSON (*.json)")
        if filename:self.load(Path(filename),merge)

    def save(self):
        default=(self.path.with_name(self.path.stem+"-edited.json") if self.path
                 else Path.home()/"Documents"/"genesis-pose.json")
        filename,_=QFileDialog.getSaveFileName(self,"Save pose JSON",str(default),"Pose JSON (*.json)")
        if not filename:return False
        try:
            path=Path(filename)
            if not path.suffix:
                path=path.with_suffix(".json")
                if path.exists() and QMessageBox.question(self,"Replace file?",str(path)+" already exists. Replace it?")!=QMessageBox.StandardButton.Yes:
                    return False
            document=validate_document(self.document)
            atomic_write(path,(json.dumps(document,indent=2,allow_nan=False)+"\n").encode("utf-8"))
            self.path=path
            self.saved=deepcopy(self.document)
            self.refresh()
            return True
        except (OSError,ValueError) as exc:
            self.error(exc)
            return False

    def export_png(self):
        filename,_=QFileDialog.getSaveFileName(self,"Export skeleton PNG",
            str(Path.home()/"Documents"/"genesis-skeleton.png"),"PNG image (*.png)")
        if not filename:return
        try:
            path=Path(filename)
            if not path.suffix:
                path=path.with_suffix(".png")
                if path.exists() and QMessageBox.question(self,"Replace file?",str(path)+" already exists. Replace it?")!=QMessageBox.StandardButton.Yes:
                    return
            image=QImage(self.document["canvas_width"],self.document["canvas_height"],QImage.Format.Format_RGB32)
            if image.isNull():raise ValueError("Unable to allocate the export image.")
            image.fill(QColor("black"))
            p=QPainter(image)
            self.canvas.draw(p)
            p.end()
            writer=QSaveFile(str(path))
            if not writer.open(QIODevice.OpenModeFlag.WriteOnly):
                raise OSError(writer.errorString())
            if not image.save(writer,"PNG"):
                writer.cancelWriting()
                raise OSError("PNG encoding failed.")
            if not writer.commit():raise OSError(writer.errorString())
            self.status.setText("Skeleton PNG exported: "+str(path))
        except (OSError,ValueError) as exc:self.error(exc)

    def add_person(self):
        if len(self.document["people"])>=32:
            self.error("Maximum 32 people per document.")
            return
        doc=deepcopy(self.document)
        doc["people"].append(standing_person(doc["canvas_width"],doc["canvas_height"],len(doc["people"])))
        self.change(doc)
        self.person.setCurrentIndex(self.person.count()-1)

    def remove_person(self):
        index=self.person.currentIndex()
        if index<0:return
        doc=deepcopy(self.document)
        del doc["people"][index]
        self.change(doc)

    def make_hands(self):
        index=self.person.currentIndex()
        if index<0:return
        doc=deepcopy(self.document)
        add_hands(doc["people"][index],doc["canvas_width"],doc["canvas_height"])
        self.change(doc)

    def choose_reference(self):
        from genesis.qt_media_picker import choose_image
        filename = choose_image("GENESIS · Reference image")
        if filename:self.load_reference(Path(filename))

    def load_reference(self,path):
        reader=QImageReader(str(path))
        reader.setAutoTransform(True)
        size=reader.size()
        if size.width()*size.height()>32_000_000:
            self.error("Reference image exceeds 32 megapixels.")
            return
        image=reader.read()
        if image.isNull():
            self.error("Cannot read this reference image.")
            return
        self.reference=image
        self.reference_path=path
        self.extract_button.setEnabled(self.extractor is None)
        self.canvas.update()


    def extract_cpu(self):
        if self.reference_path is None or self.extractor is not None:
            return
        weights=Path.home()/"AI"/"ComfyUI"/"custom_nodes"/"comfyui_controlnet_aux"/"ckpts"/"yzd-v"/"DWPose"
        if not (weights/"yolox_l.onnx").is_file() or not (weights/"dw-ll_ucoco_384.onnx").is_file():
            self.error("DWPose detector weights are unavailable.")
            return
        runner=Path.home()/"miniforge3"/"envs"/"comfyui-reactor-rocm"/"bin"/"python"
        if not runner.is_file():
            self.error("The local ComfyUI Python environment is unavailable.")
            return
        process=QProcess(self)
        environment=QProcessEnvironment.systemEnvironment()
        for key in ("HIP_VISIBLE_DEVICES","ROCR_VISIBLE_DEVICES","CUDA_VISIBLE_DEVICES"):
            environment.insert(key,"-1")
        environment.insert("AUX_ORT_PROVIDERS","CPUExecutionProvider")
        environment.insert("OMP_NUM_THREADS","2")
        process.setProcessEnvironment(environment)
        process.setWorkingDirectory(str(Path(__file__).resolve().parents[1]))
        process.finished.connect(self._extraction_finished)
        process.errorOccurred.connect(self._extraction_error)
        self.extractor=process
        self.cancelled=False
        self.extract_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText("Extracting joints on CPU… the editor remains responsive.")
        process.start(str(runner),["-m","genesis.pose_extract_cpu",str(self.reference_path)])
        self.extract_timer.start(90000)

    def _extraction_error(self,error):
        if error==QProcess.ProcessError.FailedToStart and self.extractor is not None:
            failed=self.extractor
            self.extractor=None
            self.extract_timer.stop()
            self.cancel_button.setEnabled(False)
            self.extract_button.setEnabled(self.reference_path is not None)
            self.error("Could not start the local CPU DWPose worker: "+failed.errorString())
            failed.deleteLater()

    def cancel_extraction(self):
        if self.extractor is not None and self.extractor.state()!=QProcess.ProcessState.NotRunning:
            self.cancelled=True
            self.extractor.kill()
            self.status.setText("DWPose extraction cancelled.")
        self.extract_timer.stop()

    def _extraction_finished(self,exit_code,status):
        self.extract_timer.stop()
        process=self.extractor
        if process is None:return
        output=bytes(process.readAllStandardOutput()).decode("utf-8",errors="replace")
        errors=bytes(process.readAllStandardError()).decode("utf-8",errors="replace")
        process.deleteLater()
        self.extractor=None
        self.cancel_button.setEnabled(False)
        self.extract_button.setEnabled(self.reference_path is not None)
        if self.cancelled:
            self.status.setText("DWPose extraction cancelled.")
            return
        if exit_code or status!=QProcess.ExitStatus.NormalExit:
            self.error(errors.strip().splitlines()[-1] if errors.strip() else "DWPose extraction failed.")
            return
        try:
            document=validate_document(json.loads(output))
            if not document["people"]:
                raise ValueError("No people detected in the reference image.")
            self.change(document)
            self.canvas.fit()
            self.status.setText(f"Extracted {len(document['people'])} editable person(s) on CPU. Save JSON to keep them.")
        except (ValueError,TypeError) as exc:self.error(exc)


class SkeletonEditorBridge(QObject):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.editor=None

    @pyqtSlot(str)
    def openEditor(self,source=""):
        if self.editor is None:
            self.editor=SkeletonEditor()
        editor=self.editor
        # Existing unsaved edits take priority over switching library references.
        if source and editor.document==editor.saved:
            try:
                path=local_path(source)
                if path.suffix.lower()==".json":
                    editor.load(path)
                elif path.is_file():
                    sidecar=path.with_suffix(".json")
                    if sidecar.is_file():
                        if not editor.load(sidecar):
                            return
                    editor.load_reference(path)
            except (OSError,ValueError) as exc:editor.error(exc)
        editor.show()
        editor.raise_()
        editor.activateWindow()

    @pyqtSlot(result=bool)
    def confirmClose(self):
        return self.editor is None or self.editor.confirm_close()
