import { BrowserRouter, Routes, Route } from 'react-router-dom'

import Home from './pages/Home'
import Host from './pages/Host'
import Join from './pages/Join'
import Play from './pages/Play'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/host" element={<Host />} />
        <Route path="/join" element={<Join />} />
        <Route path="/play" element={<Play />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
