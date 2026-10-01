import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: canvasWorkspace
    objectName: "canvasWorkspace"
    property url sourceUrl: ""
    property real zoom: 1
    property bool resizeMode: false
    property bool panelsVisible: true
    signal homeRequested()
    readonly property bool compact: width < 1100
    readonly property var selection: canvasBridge.selected
    onSourceUrlChanged: if (sourceUrl.toString().length) canvasBridge.addSourceOnce(sourceUrl.toString())
    Component.onCompleted: if (sourceUrl.toString().length) canvasBridge.addSourceOnce(sourceUrl.toString())

    Shortcut { sequence: "Ctrl+Z"; enabled: canvasWorkspace.visible && canvasBridge.canUndo; onActivated: canvasBridge.undo() }
    Shortcut { sequence: "Ctrl+Shift+Z"; enabled: canvasWorkspace.visible && canvasBridge.canRedo; onActivated: canvasBridge.redo() }
    Shortcut { sequence: "Ctrl+S"; enabled: canvasWorkspace.visible; onActivated: canvasBridge.saveProject() }

    component Action: Button {
        palette.buttonText: "#e9e6df"
        padding: 9
        background: Rectangle {
            radius: 5
            color: parent.down ? "#51412b" : parent.hovered ? "#302719" : "#202020"
            border.color: parent.enabled ? "#635035" : "#343434"
        }
    }
    component Caption: Label { color: "#c5a267"; font.pixelSize: 10; font.letterSpacing: 1.3 }
    component ValueInput: TextField {
        color: "#eee7dc"; font.pixelSize: 12; selectByMouse: true
        implicitWidth: 75; padding: 7
        background: Rectangle { color: "#090909"; radius: 4; border.color: "#4a4033" }
        validator: DoubleValidator { bottom: -32000; top: 32000; decimals: 1; locale: "C" }
    }

    Dialog {
        id: sizeDialog
        objectName: "canvasSizeDialog"
        property bool creating: true
        anchors.centerIn: parent
        modal: true
        title: creating ? "New canvas" : "Canvas size"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (creating) canvasBridge.createProject(canvasWidthInput.value, canvasHeightInput.value)
            else canvasBridge.setCanvasSize(canvasWidthInput.value, canvasHeightInput.value)
            canvasWorkspace.zoom = 1
        }
        ColumnLayout {
            Label { text: "Transparent canvas · dimensions in pixels" }
            ComboBox {
                model: ["Custom", "Square · 1024 × 1024", "Portrait · 768 × 1152", "Landscape · 1920 × 1080", "4K · 3840 × 2160"]
                onActivated: {
                    var sizes = [[0,0], [1024,1024], [768,1152], [1920,1080], [3840,2160]]
                    if (currentIndex > 0) { canvasWidthInput.value = sizes[currentIndex][0]; canvasHeightInput.value = sizes[currentIndex][1] }
                }
            }
            RowLayout { Label { text: "Width" } SpinBox { id: canvasWidthInput; objectName: "canvasWidthInput"; from: 1; to: 16384; value: 3840; editable: true } }
            RowLayout { Label { text: "Height" } SpinBox { id: canvasHeightInput; objectName: "canvasHeightInput"; from: 1; to: 16384; value: 2160; editable: true } }
            Label { text: "Up to 32 megapixels. Changing size keeps layer positions." }
        }
    }

    ColumnLayout {
        anchors.fill: parent; spacing: 10
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                Label { text: "CANVAS" + (canvasBridge.dirty ? "  •" : ""); color: "#f3d28b"; font.pixelSize: 24; font.bold: true; font.letterSpacing: 2 }
                Label { text: "Arrange images. Build the composition."; color: "#aaa7a1"; font.pixelSize: 12 }
            }
            Action { text: "⌂ Home"; onClicked: canvasWorkspace.homeRequested() }
            Action { text: canvasWorkspace.panelsVisible ? "Hide panels" : "Show panels"; onClicked: canvasWorkspace.panelsVisible = !canvasWorkspace.panelsVisible }
            Caption { text: "LOCAL COMPOSITION" }
            Action { objectName: "undoButton"; text: "Undo"; enabled: canvasBridge.canUndo; onClicked: canvasBridge.undo() }
            Action { objectName: "redoButton"; text: "Redo"; enabled: canvasBridge.canRedo; onClicked: canvasBridge.redo() }
        }
        Flow {
            Layout.fillWidth: true; Layout.preferredHeight: childrenRect.height
            spacing: 7
            Action { text: "＋ Add image / cutout"; onClicked: canvasBridge.chooseLayer() }
            Action { objectName: "canvasNewButton"; text: "New…"; enabled: !canvasBridge.busy; onClicked: { sizeDialog.creating = true; canvasWidthInput.value = 3840; canvasHeightInput.value = 2160; sizeDialog.open() } }
            Action { text: "Canvas size…"; enabled: canvasBridge.canvasWidth > 0 && !canvasBridge.busy; onClicked: { sizeDialog.creating = false; canvasWidthInput.value = canvasBridge.canvasWidth; canvasHeightInput.value = canvasBridge.canvasHeight; sizeDialog.open() } }
            Action { text: "↖ Move"; checkable: true; checked: !canvasWorkspace.resizeMode; onClicked: canvasWorkspace.resizeMode = false }
            Action { objectName: "canvasResizeTool"; text: "⤢ Resize"; checkable: true; checked: canvasWorkspace.resizeMode; onClicked: canvasWorkspace.resizeMode = true }
            Action { text: "Open project"; onClicked: canvasBridge.openProject() }
            Action { text: "Save project"; enabled: canvasBridge.canvasWidth > 0; onClicked: canvasBridge.saveProject() }
            Action { text: "Export PNG"; enabled: canvasBridge.canvasWidth > 0; onClicked: canvasBridge.exportPng() }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
            Rectangle {
                visible: canvasWorkspace.panelsVisible
                Layout.preferredWidth: canvasWorkspace.compact ? 150 : 175; Layout.fillHeight: true
                color: "#141414"; radius: 8; border.color: "#343434"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Caption { Layout.fillWidth: true; text: "LAYERS" }
                        Label { text: canvasBridge.layers.length; color: "#aaa7a1" }
                    }
                    Label { Layout.fillWidth: true; text: "Top layer shown first"; color: "#81796b"; font.pixelSize: 10 }
                    ListView {
                        id: layerList
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
                        model: canvasBridge.layers.slice().reverse()
                        delegate: Rectangle {
                            required property var modelData
                            width: layerList.width; height: 79; radius: 5
                            color: canvasWorkspace.selection.id === modelData.id ? "#302719" : "#1c1c1c"
                            border.color: canvasWorkspace.selection.id === modelData.id ? "#c5a267" : "#343434"
                            MouseArea { anchors.fill: parent; onClicked: canvasBridge.selectLayer(modelData.id) }
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 7; spacing: 7
                                Image { Layout.preferredWidth: 43; Layout.preferredHeight: 54; source: modelData.source; fillMode: Image.PreserveAspectFit; sourceSize.width: 100; sourceSize.height: 100; asynchronous: true; autoTransform: true }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 3
                                    Label { Layout.fillWidth: true; text: modelData.name; color: "#eee7dc"; elide: Text.ElideMiddle; font.pixelSize: 11 }
                                    Label { text: Math.round(modelData.opacity * 100) + "% opacity"; color: "#aaa7a1"; font.pixelSize: 10 }
                                    CheckBox { text: "Visible"; checked: modelData.visible; padding: 0; font.pixelSize: 10; palette.windowText: "#aaa7a1"; onClicked: canvasBridge.setVisible(modelData.id, checked) }
                                }
                            }
                        }
                        ScrollBar.vertical: ScrollBar { }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Action { Layout.fillWidth: true; text: "Raise"; enabled: !!canvasWorkspace.selection.id; onClicked: canvasBridge.reorderSelected(1) }
                        Action { Layout.fillWidth: true; text: "Lower"; enabled: !!canvasWorkspace.selection.id; onClicked: canvasBridge.reorderSelected(-1) }
                    }
                    Action { Layout.fillWidth: true; text: "Remove layer"; enabled: !!canvasWorkspace.selection.id; onClicked: canvasBridge.removeSelected() }
                }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                color: "#090909"; radius: 8; border.color: "#343434"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Caption { Layout.fillWidth: true; text: canvasBridge.canvasWidth ? canvasBridge.canvasWidth + " × " + canvasBridge.canvasHeight : "COMPOSITION" }
                        Action { text: "−"; enabled: canvasWorkspace.zoom > 0.25; onClicked: canvasWorkspace.zoom = Math.max(0.25, canvasWorkspace.zoom / 1.25) }
                        Label { text: Math.round(canvasWorkspace.zoom * 100) + "%"; color: "#aaa7a1"; font.pixelSize: 10; Layout.preferredWidth: 36; horizontalAlignment: Text.AlignHCenter }
                        Action { text: "+"; enabled: canvasWorkspace.zoom < 4; onClicked: canvasWorkspace.zoom = Math.min(4, canvasWorkspace.zoom * 1.25) }
                        Action { text: "Fit"; onClicked: { canvasWorkspace.zoom = 1; stage.contentX = 0; stage.contentY = 0 } }
                    }
                    Flickable {
                        id: stage
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        readonly property real fitScale: canvasBridge.canvasWidth ? Math.min(width / canvasBridge.canvasWidth, height / canvasBridge.canvasHeight) : 1
                        readonly property real documentScale: fitScale * canvasWorkspace.zoom
                        contentWidth: Math.max(width, composition.width)
                        contentHeight: Math.max(height, composition.height)
                        boundsBehavior: Flickable.StopAtBounds
                        Rectangle {
                            id: composition
                            objectName: "composition"
                            x: Math.max(0, (stage.width - width) / 2)
                            y: Math.max(0, (stage.height - height) / 2)
                            width: canvasBridge.canvasWidth * stage.documentScale
                            height: canvasBridge.canvasHeight * stage.documentScale
                            visible: canvasBridge.canvasWidth > 0
                            color: "#2d2d2d"; clip: true
                            Canvas {
                                anchors.fill: parent
                                onWidthChanged: requestPaint()
                                onHeightChanged: requestPaint()
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)
                                    for (var y = 0; y < height; y += 20)
                                        for (var x = 0; x < width; x += 20) {
                                            ctx.fillStyle = ((x / 20 + y / 20) % 2) ? "#353535" : "#282828"
                                            ctx.fillRect(x, y, 20, 20)
                                        }
                                }
                            }
                            Repeater {
                                model: canvasBridge.layers
                                delegate: Item {
                                    id: layerItem
                                    objectName: "canvasLayerItem"
                                    required property var modelData
                                    property real dragX: 0
                                    property real dragY: 0
                                    property real resizeFactor: 1
                                    x: modelData.x * stage.documentScale + dragX
                                    y: modelData.y * stage.documentScale + dragY
                                    width: modelData.width * stage.documentScale * resizeFactor
                                    height: modelData.height * stage.documentScale * resizeFactor
                                    visible: modelData.visible
                                    rotation: modelData.rotation || 0
                                    transformOrigin: Item.Center
                                    Image { objectName: "layerPreview"; smooth: layerItem.resizeFactor === 1; anchors.fill: parent; source: layerItem.modelData.source; opacity: layerItem.modelData.opacity; fillMode: Image.Stretch; asynchronous: true; autoTransform: true; sourceSize.width: 1600; sourceSize.height: 1600 }
                                    Rectangle { anchors.fill: parent; color: "transparent"; border.color: "#e5bd75"; border.width: 1; visible: canvasWorkspace.selection.id === layerItem.modelData.id }
                                    MouseArea {
                                        anchors.fill: parent; preventStealing: true; cursorShape: canvasWorkspace.resizeMode ? Qt.ArrowCursor : Qt.SizeAllCursor
                                        property point pressPoint
                                        onPressed: function(mouse) { pressPoint = mapToItem(composition, mouse.x, mouse.y) }
                                        onPositionChanged: function(mouse) {
                                            if (pressed && !canvasWorkspace.resizeMode) {
                                                var p = mapToItem(composition, mouse.x, mouse.y)
                                                layerItem.dragX += p.x - pressPoint.x
                                                layerItem.dragY += p.y - pressPoint.y
                                                pressPoint = p
                                            }
                                        }
                                        onReleased: {
                                            var layerId = layerItem.modelData.id
                                            var newX = layerItem.modelData.x + layerItem.dragX / stage.documentScale
                                            var newY = layerItem.modelData.y + layerItem.dragY / stage.documentScale
                                            layerItem.dragX = 0; layerItem.dragY = 0
                                            canvasBridge.moveLayer(layerId, newX, newY)
                                            canvasBridge.selectLayer(layerId)
                                        }
                                        onCanceled: { layerItem.dragX = 0; layerItem.dragY = 0 }
                                    }
                                    Rectangle {
                                        objectName: "layerResizeHandle"
                                        anchors.right: parent.right; anchors.bottom: parent.bottom
                                        width: 24; height: 24; radius: 3; color: "#e5bd75"
                                        visible: canvasWorkspace.resizeMode && canvasWorkspace.selection.id === layerItem.modelData.id
                                        MouseArea {
                                            anchors.fill: parent; preventStealing: true; cursorShape: Qt.SizeFDiagCursor
                                            property point initial
                                            property real originalWidth
                                            property real originalHeight
                                            onPressed: function(mouse) {
                                                initial = mapToItem(composition, mouse.x, mouse.y)
                                                originalWidth = layerItem.width
                                                originalHeight = layerItem.height
                                            }
                                            function previewResize(mouse) {
                                                var point = mapToItem(composition, mouse.x, mouse.y)
                                                var angle = -layerItem.rotation * Math.PI / 180
                                                var dx = point.x - initial.x
                                                var dy = point.y - initial.y
                                                var localX = dx * Math.cos(angle) - dy * Math.sin(angle)
                                                var localY = dx * Math.sin(angle) + dy * Math.cos(angle)
                                                // Preview only: commit once on release, preserving undo granularity.
                                                var factor = 1 + (localX * originalWidth + localY * originalHeight) / (originalWidth * originalWidth + originalHeight * originalHeight)
                                                var row = layerItem.modelData
                                                var limit = Math.min(16384 / row.width, 16384 / row.height, Math.sqrt(32000000 / (row.width * row.height)))
                                                layerItem.resizeFactor = Math.max(Math.max(1 / row.width, 1 / row.height), Math.min(limit, factor))
                                            }
                                            onPositionChanged: function(mouse) { if (pressed) previewResize(mouse) }
                                            onReleased: function(mouse) {
                                                previewResize(mouse)
                                                var factor = layerItem.resizeFactor
                                                layerItem.resizeFactor = 1
                                                canvasBridge.resizeSelected(factor)
                                            }
                                            onCanceled: layerItem.resizeFactor = 1
                                        }
                                    }
                                }
                            }
                        }
                        Column {
                            anchors.centerIn: parent; spacing: 12; visible: canvasBridge.canvasWidth === 0
                            Label { anchors.horizontalCenter: parent.horizontalCenter; text: "＋"; color: "#c5a267"; font.pixelSize: 48 }
                            Label { anchors.horizontalCenter: parent.horizontalCenter; text: "Create a canvas or add an image"; color: "#eee7dc"; font.pixelSize: 19 }
                            Label { anchors.horizontalCenter: parent.horizontalCenter; text: "Stack cutouts and arrange your scene"; color: "#aaa7a1"; font.pixelSize: 11 }
                        }
                        ScrollBar.vertical: ScrollBar { }
                        ScrollBar.horizontal: ScrollBar { }
                    }
                    Label { Layout.fillWidth: true; text: canvasWorkspace.resizeMode ? "Drag the gold corner to resize · Size fields give exact pixels" : "Move tool · Drag an image to reposition it"; color: "#81796b"; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap }
                }
            }
            Rectangle {
                visible: canvasWorkspace.panelsVisible
                Layout.preferredWidth: canvasWorkspace.compact ? 180 : 210; Layout.fillHeight: true
                color: "#141414"; radius: 8; border.color: "#343434"
                ScrollView {
                    anchors.fill: parent; anchors.margins: 14; clip: true; contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width; spacing: 14
                        Caption { text: "SELECTED LAYER" }
                        TextField {
                            Layout.fillWidth: true
                            text: canvasWorkspace.selection.name || ""
                            placeholderText: "Choose a layer"
                            enabled: !!canvasWorkspace.selection.id
                            color: "#eee7dc"; selectByMouse: true; maximumLength: 256
                            onEditingFinished: if (text.trim().length) canvasBridge.renameSelected(text)
                            background: Rectangle { color: "#090909"; radius: 4; border.color: "#4a4033" }
                        }
                        Caption { text: "SELECTED IMAGE TOOLS" }
                        Action { Layout.fillWidth: true; text: "Remove background"; enabled: !!canvasWorkspace.selection.id && !canvasBridge.busy; onClicked: canvasBridge.processSelected("background remover", 2) }
                        Action { Layout.fillWidth: true; text: "AI upscale 2×"; enabled: !!canvasWorkspace.selection.id && !canvasBridge.busy; onClicked: canvasBridge.processSelected("upscale", 2) }
                        Action { Layout.fillWidth: true; text: "AI upscale 4×"; enabled: !!canvasWorkspace.selection.id && !canvasBridge.busy; onClicked: canvasBridge.processSelected("upscale", 4) }
                        Action { Layout.fillWidth: true; text: "8× output · 4× AI"; enabled: !!canvasWorkspace.selection.id && !canvasBridge.busy; onClicked: canvasBridge.processSelected("upscale", 8) }
                        Action { Layout.fillWidth: true; text: "Standard resize 2×"; enabled: !!canvasWorkspace.selection.id && !canvasBridge.busy; onClicked: canvasBridge.processSelected("standard resize", 2) }
                        Label { Layout.fillWidth: true; text: "Results stay in Canvas; choose a destination when saving or exporting. The original remains as a hidden layer. AI upscale uses the selected backend."; color: "#aaa7a1"; font.pixelSize: 11; wrapMode: Text.Wrap }
                        Caption { text: "POSITION / PX" }
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "X"; color: "#aaa7a1" }
                            ValueInput { Layout.fillWidth: true; enabled: !!canvasWorkspace.selection.id; text: Math.round(canvasWorkspace.selection.x || 0); onEditingFinished: if (acceptableInput) canvasBridge.moveLayer(canvasWorkspace.selection.id, Number(text), canvasWorkspace.selection.y) }
                            Label { text: "Y"; color: "#aaa7a1" }
                            ValueInput { Layout.fillWidth: true; enabled: !!canvasWorkspace.selection.id; text: Math.round(canvasWorkspace.selection.y || 0); onEditingFinished: if (acceptableInput) canvasBridge.moveLayer(canvasWorkspace.selection.id, canvasWorkspace.selection.x, Number(text)) }
                        }
                        Caption { text: "LAYER SIZE / PX" }
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "W"; color: "#aaa7a1" }
                            ValueInput { Layout.fillWidth: true; enabled: !!canvasWorkspace.selection.id; text: Math.round(canvasWorkspace.selection.width || 0); validator: IntValidator { bottom: 1; top: 16384 } onEditingFinished: if (acceptableInput) canvasBridge.setSelectedSize(Number(text), canvasWorkspace.selection.height) }
                            Label { text: "H"; color: "#aaa7a1" }
                            ValueInput { Layout.fillWidth: true; enabled: !!canvasWorkspace.selection.id; text: Math.round(canvasWorkspace.selection.height || 0); validator: IntValidator { bottom: 1; top: 16384 } onEditingFinished: if (acceptableInput) canvasBridge.setSelectedSize(canvasWorkspace.selection.width, Number(text)) }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Action { Layout.fillWidth: true; text: "Smaller"; enabled: !!canvasWorkspace.selection.id; onClicked: canvasBridge.resizeSelected(0.9) }
                            Action { Layout.fillWidth: true; text: "Larger"; enabled: !!canvasWorkspace.selection.id; onClicked: canvasBridge.resizeSelected(1.1) }
                        }
                        Caption { text: "ROTATE / COPY" }
                        Label { text: canvasWorkspace.selection.id ? Math.round(canvasWorkspace.selection.rotation || 0) + "°" : "—"; color: "#aaa7a1"; font.pixelSize: 12 }
                        RowLayout {
                            Layout.fillWidth: true
                            Action { Layout.fillWidth: true; text: "↶ 90°"; enabled: !!canvasWorkspace.selection.id; onClicked: canvasBridge.rotateSelected(-90) }
                            Action { Layout.fillWidth: true; text: "↷ 90°"; enabled: !!canvasWorkspace.selection.id; onClicked: canvasBridge.rotateSelected(90) }
                        }
                        Action { Layout.fillWidth: true; text: "Duplicate layer"; enabled: !!canvasWorkspace.selection.id; onClicked: canvasBridge.duplicateSelected() }
                        Caption { text: "OPACITY" }
                        Slider { Layout.fillWidth: true; enabled: !!canvasWorkspace.selection.id; from: 0; to: 1; stepSize: 0.01; value: canvasWorkspace.selection.opacity === undefined ? 1 : canvasWorkspace.selection.opacity; onPressedChanged: if (!pressed) canvasBridge.setOpacity(value) }
                        Label { text: Math.round((canvasWorkspace.selection.opacity === undefined ? 1 : canvasWorkspace.selection.opacity) * 100) + "%"; color: "#aaa7a1"; font.pixelSize: 12 }
                        Rectangle { Layout.fillWidth: true; height: 1; color: "#343434" }
                        Caption { text: "SOURCE PROTECTION" }
                        Label { Layout.fillWidth: true; text: "Your originals stay unchanged. Save a project to keep layers editable, or export a transparent PNG."; color: "#aaa7a1"; font.pixelSize: 11; wrapMode: Text.Wrap }

                    }
                }
            }
        }
        Label { Layout.fillWidth: true; text: canvasBridge.status; color: "#c5a267"; font.pixelSize: 11; elide: Text.ElideRight }
    }
}
