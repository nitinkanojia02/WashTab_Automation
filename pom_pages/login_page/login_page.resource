*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${USER_NAME_TEXTBOX}    xpath=//input[@placeholder='User Name']
${PASSWORD_TEXTBOX}    xpath=//input[@placeholder='Password']
${SIGN_IN_BUTTON}    xpath=//ion-button[normalize-space(.)='SIGN IN']
${VALID_USERNAME}    haklarr
${VALID_PASSWORD}    Icstunnel1
${INVALID_USERNAME}    wronguser
${INVALID_PASSWORD}    wrongpass
${INVALID_USERNAME_ALT}    invaliduser
${INVALID_PASSWORD_ALT}    invalidpass
${BLANK_USERNAME}    ${EMPTY}
${BLANK_PASSWORD}    ${EMPTY}
${SPACE_USERNAME}    ${SPACE}${SPACE}${SPACE}
${SPACE_PASSWORD}    ${SPACE}${SPACE}${SPACE}
${USERNAME_WITH_SPACES}    ${SPACE}${SPACE}haklarr${SPACE}${SPACE}
${PASSWORD_WITH_SPACES}    ${SPACE}${SPACE}Icstunnel1${SPACE}${SPACE}
${SPECIAL_USERNAME}    haklarr!@#
${SPECIAL_PASSWORD}    Icstunnel1!@#
${UPPERCASE_USERNAME}    HAKLARR
${LOWERCASE_PASSWORD}    icstunnel1
${LONG_USERNAME}    haklarr_haklarr_haklarr_haklarr_haklarr_haklarr_haklarr
${LONG_PASSWORD}    Icstunnel1Icstunnel1Icstunnel1Icstunnel1Icstunnel1
*** Keywords ***
Verify Login Page Loaded
    Wait For Element To Be Ready    ${USER_NAME_TEXTBOX}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}

Enter User Name
    [Arguments]    ${text}
    Input Text When Ready    ${USER_NAME_TEXTBOX}    ${text}

Enter Password
    [Arguments]    ${text}
    Input Text When Ready    ${PASSWORD_TEXTBOX}    ${text}

Click Sign In Button
    Click When Ready    ${SIGN_IN_BUTTON}

Submit Login With Enter Key
    Press Keys    ${PASSWORD_TEXTBOX}    ENTER

Click Sign In Button Multiple Times
    [Arguments]    ${count}=3
    FOR    ${index}    IN RANGE    ${count}
        Click When Ready    ${SIGN_IN_BUTTON}
    END

Verify Username Required Validation
    Wait For Element To Be Ready    ${USER_NAME_TEXTBOX}

Verify Password Required Validation
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}

Verify Password Field Is Masked
    ${type}=    Get Element Attribute    ${PASSWORD_TEXTBOX}    type
    Should Be Equal    ${type}    password
