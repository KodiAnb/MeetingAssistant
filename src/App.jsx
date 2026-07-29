import { useState, useEffect, Fragment } from 'react'
import { Routes, Route } from 'react-router-dom'
import { useNavigate, useLocation, useParams } from 'react-router-dom'
import './App.css'


function Uploading({ file, setFile, setMeetingId }) {
  const navigate = useNavigate()
  const [load, setLoad] = useState(false)
  const [truefile, settruefile] = useState(false)

  function handleChange(event) {    
    const selected = event.target.files[0]
    if (selected && selected.type.startsWith('video/')) {
      setFile(selected)
      settruefile(true)
      return 
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    console.log(truefile)
    async function submit(formData) {
      try {
        const response = await fetch('/upload', {
          method: 'POST',
          body: formData,
        })
        const data = await response.json()
        setMeetingId(data.id)
        navigate(`/upload-complete/${data.id}`)
      } finally {
        setLoad(false)
      }
    }

    if (truefile == true){
      console.log("hi")
      const formData = new FormData()
      formData.append("video", file)
      submit(formData)
      
      setLoad(true)
    } else{
      setLoad(false)
    } 
  }

  return (
    <div style={{marginTop:"25%"}}>
      <form onSubmit={handleSubmit}>
        <input type="file" onChange={handleChange} />
        <button className='getstarted' type="submit">Submit</button> 
        {load && <div className="loader"></div>} 
      </form>
    </div>
  )
}


function HomePage() {
  const navigate = useNavigate()

  function handleClick() {
    navigate('/upload')
  }

  return (
    <>
      <h1 style={{marginTop: "30px"}}>Meeting Assistant</h1>
      <p className='pad'>Welcome! Click below to upload your file.</p>
      <button className='getstarted' onClick={handleClick}>Get Started</button>
    </>
  )
}


function Task({ name, description, onSelect }) {
  return (
    <div className="item" onClick={() => onSelect(name, description)}>
      <p className="item_content" style={{ top: '10%' }}>{name}</p>
      <p className="item_content" style={{ left: '25%', textAlign: 'left'}}>{description}</p>
    </div>
  );
}

function TaskList() {
  const { meetingId } = useParams()
  const [app_dicts, setappdicts] = useState(null)
  const [app, setApp] = useState(1)
  const navigate = useNavigate()

  useEffect(() => { //to wait until component is mounted
    async function send() {
      const response = await fetch(`/upload-complete/${meetingId}`, { method: 'GET' })
      const data = await response.json()
      setappdicts([data.google_document, data.google_slides, data.gmail, data.calendar, data.miscellaneous])
    }
    send()
  }, [meetingId])

  function CreateItem(name, description) {
    navigate("/gsuite", { state: { info: [name, description, app, meetingId] } })
  }

  if (!app_dicts) return <div>Loading...</div>
  let chosen_dict = app_dicts[app]


  function fil(pair){
    return pair != undefined
  }

  chosen_dict = chosen_dict.filter(fil)

  function backButton(event){
    navigate("/upload")
  }

  return (
    <>
      <h1 style={{ color: 'white' }}>Task List</h1>
      <div className="browser-window">
        <div className="tab-bar">
          <div className={app === 0 ? "tab-item active" : "tab-item"} onClick={() => setApp(0)}><p>google docs</p></div>
          <div className={app === 1 ? "tab-item active" : "tab-item"} onClick={() => setApp(1)}><p>google slides</p></div>
          <div className={app === 2 ? "tab-item active" : "tab-item"} onClick={() => setApp(2)}><p>gmail</p></div>
          <div className={app === 3 ? "tab-item active" : "tab-item"} onClick={() => setApp(3)}><p>google calendar</p></div>
          <div className={app === 4 ? "tab-item active" : "tab-item"} onClick={() => setApp(4)}><p>miscellaneous</p></div>
        </div>
        <div className="tab-content">
          {chosen_dict
            .map((x, index) => (
              <Task key={index} name={x.name} description={x.description} onSelect={CreateItem} />
          ))}
        </div>
      </div>
      <button className='getstarted' onClick={backButton}> Use another Meeting </button>
    </>
  )
}

function Gsuite(){
  const location = useLocation();
  const information = location.state?.info;
  const navigate = useNavigate()

  useEffect(() => {
    async function submit(inf) {
      const response = await fetch('/gsuite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ Name: inf[0], Description: inf[1], Suite: inf[2] }),
      })
      if (!response.ok) return
      const data = await response.json()
      if (data.url) window.open(data.url, "_blank")
    }
    if (information) submit(information)
  }, [information])

  const handleClick = () => {
    navigate(`/upload-complete/${information[3]}`)
  };


  return(
    <>
      <h1>Your Google App is loading!</h1>
      <button onClick={handleClick}>Go back</button>
    </>
  )
}

export default function App() {
  
  const [meetingId, setMeetingId] = useState(null)
  const [file, setFile] = useState(null)
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/upload" element={<Uploading file={file} setFile={setFile} setMeetingId={setMeetingId}/>} />
      <Route path="/upload-complete/:meetingId" element={<TaskList />} />
      <Route path="/gsuite" element={<Gsuite />}/>
    </Routes>
  )
  

  
}
