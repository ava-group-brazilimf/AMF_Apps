export async function writeInReport(_reponse) {
    console.info("Response Head: \n")
    console.log(_reponse);
    console.info("\n Response Body: \n")
    try {  
        console.log(await _reponse.json());
    }
    catch (e: unknown) { 
        console.info(" null. \n")
    }
}

export async function takeScreeshot(_page, _testInfo) {
    const screenshot = await _page.screenshot();
    await _testInfo.attach('screenshot', { body: screenshot, contentType: 'image/png' });
}